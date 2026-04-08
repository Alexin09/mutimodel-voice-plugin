"""
OpenAI Whisper 引擎 — 本地离线 ASR

特点：
- 完全离线，无需网络
- 多语言支持（含中英混排）
- 模型可选：tiny/base/small/medium/large-v3
- 支持 faster-whisper 加速推理
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

from .base import ASRResult, BaseASREngine
from .registry import EngineRegistry

logger = logging.getLogger(__name__)


@dataclass
class WhisperConfig:
    """Whisper 配置"""

    model_size: str = "base"  # tiny/base/small/medium/large-v3
    device: str = "auto"  # auto/cpu/cuda/mps
    compute_type: str = "float16"  # float16/int8/float32
    language: Optional[str] = "zh"  # None = 自动检测
    use_faster_whisper: bool = True  # 使用 faster-whisper 加速
    # VAD 参数
    vad_filter: bool = True  # 启用 VAD 过滤静音段
    vad_threshold: float = 0.5


class WhisperEngine(BaseASREngine):
    """
    Whisper 本地 ASR 引擎

    支持两种后端：
    - faster-whisper (推荐，速度快 4x)
    - openai-whisper (原版)
    """

    def __init__(self, **kwargs):
        self.config = WhisperConfig(
            **{
                k: v
                for k, v in kwargs.items()
                if k in WhisperConfig.__dataclass_fields__
            }
        )
        self._model = None

    @property
    def name(self) -> str:
        return "whisper"

    @property
    def is_local(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        # Whisper 本身不支持真正的流式，但可以通过分段模拟
        return False

    async def initialize(self) -> None:
        """加载 Whisper 模型"""
        logger.info(f"Loading Whisper model: {self.config.model_size}")

        if self.config.use_faster_whisper:
            await self._init_faster_whisper()
        else:
            await self._init_openai_whisper()

        logger.info("Whisper model loaded")

    async def _init_faster_whisper(self):
        """加载 faster-whisper 模型"""

        def _load():
            from faster_whisper import WhisperModel

            return WhisperModel(
                self.config.model_size,
                device=self.config.device if self.config.device != "auto" else "auto",
                compute_type=self.config.compute_type,
            )

        self._model = await asyncio.get_event_loop().run_in_executor(None, _load)

    async def _init_openai_whisper(self):
        """加载 openai-whisper 模型"""

        def _load():
            import whisper

            return whisper.load_model(self.config.model_size)

        self._model = await asyncio.get_event_loop().run_in_executor(None, _load)

    async def recognize_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[ASRResult, None]:
        """
        伪流式识别：收集一定量音频后批量识别

        对于 Whisper，采用 VAD 分段 + 批量识别的策略
        """
        import numpy as np

        buffer = bytearray()
        min_chunk_bytes = 16000 * 2 * 3  # 至少 3 秒的音频

        async for chunk in audio_stream:
            buffer.extend(chunk)

            if len(buffer) >= min_chunk_bytes:
                audio_np = (
                    np.frombuffer(bytes(buffer), dtype=np.int16).astype(np.float32)
                    / 32768.0
                )
                result = await self._transcribe(audio_np)
                if result.text.strip():
                    yield result
                buffer.clear()

        # 处理剩余音频
        if buffer:
            audio_np = (
                np.frombuffer(bytes(buffer), dtype=np.int16).astype(np.float32)
                / 32768.0
            )
            result = await self._transcribe(audio_np)
            if result.text.strip():
                result.is_final = True
                yield result

    async def _transcribe(self, audio_np) -> ASRResult:
        """执行转写"""

        def _run():
            if self.config.use_faster_whisper:
                segments, info = self._model.transcribe(
                    audio_np,
                    language=self.config.language,
                    vad_filter=self.config.vad_filter,
                    vad_parameters={"threshold": self.config.vad_threshold},
                )
                text = " ".join(seg.text for seg in segments)
                return ASRResult(
                    text=text,
                    is_final=True,
                    language=info.language,
                    confidence=info.language_probability,
                )
            else:
                result = self._model.transcribe(
                    audio_np,
                    language=self.config.language,
                )
                return ASRResult(
                    text=result["text"],
                    is_final=True,
                    language=result.get("language"),
                    raw=result,
                )

        return await asyncio.get_event_loop().run_in_executor(None, _run)

    async def recognize(self, audio_data: bytes) -> ASRResult:
        """整段识别"""
        import numpy as np

        audio_np = (
            np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        )
        return await self._transcribe(audio_np)


# 自动注册
EngineRegistry.register("whisper", WhisperEngine)
