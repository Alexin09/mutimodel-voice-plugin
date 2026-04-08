"""
实时音频捕获 — 从麦克风（DJI Mic / 任意 USB 音频设备）捕获音频流

输出：async generator of audio chunks (bytes)

设计要点：
- 流式输出，chunk 大小可配（通常 16000 samples = 1 秒 @16kHz）
- 支持 VAD（Voice Activity Detection）可选集成
- 内置静音检测，无声时不浪费 ASR 调用
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

from .device import AudioDevice, AudioDeviceManager

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """音频捕获参数"""

    sample_rate: int = 16000  # ASR 通常要求 16kHz
    channels: int = 1  # 单声道即可
    chunk_duration_ms: int = 100  # 每个 chunk 的毫秒数
    dtype: str = "int16"  # 16-bit PCM

    @property
    def chunk_size(self) -> int:
        """每个 chunk 的采样数"""
        return int(self.sample_rate * self.chunk_duration_ms / 1000)

    @property
    def bytes_per_sample(self) -> int:
        return 2 if self.dtype == "int16" else 4


class AudioCapture:
    """
    实时音频捕获器

    Usage:
        capture = AudioCapture(device=device, config=AudioConfig())
        async for chunk in capture.stream():
            # chunk: bytes, PCM 16-bit mono 16kHz
            await asr_engine.feed(chunk)
    """

    def __init__(
        self,
        device: Optional[AudioDevice] = None,
        config: Optional[AudioConfig] = None,
        device_manager: Optional[AudioDeviceManager] = None,
    ):
        self.config = config or AudioConfig()
        self.device_manager = device_manager or AudioDeviceManager()
        self.device = device
        self._running = False
        self._queue: queue.Queue[Optional[bytes]] = queue.Queue(maxsize=100)

    def _ensure_device(self) -> AudioDevice:
        """确保有可用设备"""
        if self.device is None:
            self.device = self.device_manager.select_best_device()
        return self.device

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """
        异步生成音频 chunk 流

        Yields:
            bytes: PCM 音频数据块
        """
        device = self._ensure_device()
        logger.info(f"Starting audio capture from: {device}")

        # 在后台线程中运行 sounddevice 的阻塞流
        self._running = True
        thread = threading.Thread(target=self._capture_thread, daemon=True)
        thread.start()

        try:
            while self._running:
                try:
                    chunk = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._queue.get(timeout=0.5)
                    )
                    if chunk is None:  # 停止信号
                        break
                    yield chunk
                except queue.Empty:
                    continue
        finally:
            self.stop()

    def _capture_thread(self):
        """后台音频捕获线程"""
        try:
            import sounddevice as sd
            import numpy as np

            def callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"Audio callback status: {status}")
                # 转换为 bytes
                audio_bytes = (indata[:, 0] * 32767).astype(np.int16).tobytes()
                try:
                    self._queue.put_nowait(audio_bytes)
                except queue.Full:
                    logger.warning("Audio queue full, dropping chunk")

            with sd.InputStream(
                device=self.device.index,
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                blocksize=self.config.chunk_size,
                callback=callback,
            ):
                while self._running:
                    threading.Event().wait(0.1)

        except Exception as e:
            logger.error(f"Audio capture error: {e}")
            self._queue.put(None)  # 发送停止信号

    def stop(self):
        """停止音频捕获"""
        self._running = False
        self._queue.put(None)

    async def stream_from_file(self, file_path: str) -> AsyncGenerator[bytes, None]:
        """
        从音频文件流式读取（用于测试/离线处理）

        Args:
            file_path: 音频文件路径（WAV/MP3/...）

        Yields:
            bytes: PCM 音频数据块
        """
        import soundfile as sf

        data, sr = sf.read(file_path, dtype="int16")
        if sr != self.config.sample_rate:
            # 需要重采样
            import samplerate

            ratio = self.config.sample_rate / sr
            data = samplerate.resample(data, ratio, "sinc_best")

        chunk_size = self.config.chunk_size
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            yield chunk.tobytes()
            await asyncio.sleep(self.config.chunk_duration_ms / 1000)  # 模拟实时
