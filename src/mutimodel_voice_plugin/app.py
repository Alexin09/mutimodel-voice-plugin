"""
主应用 — 将所有模块编排在一起

Pipeline:
    DJI Mic → AudioCapture → SenseVoice ASR → PostProcess Pipeline → Output
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Optional

from .config import AppConfig, load_config
from .audio.device import AudioDeviceManager
from .audio.capture import AudioCapture, AudioConfig
from .engines.registry import EngineRegistry
from .engines.base import ASRResult
from .processors.pipeline import ProcessorPipeline
from .processors.filler_filter import FillerFilterProcessor
from .processors.dictionary_replace import DictionaryReplaceProcessor
from .processors.llm_polish import LLMPolishProcessor, LLMPolishConfig
from .dictionary.manager import DictionaryManager
from .hotkey.listener import HotkeyListener, HotkeyConfig, HotkeyMode

logger = logging.getLogger(__name__)


class VoiceApp:
    """
    主应用类

    Usage:
        app = VoiceApp()          # 自动加载 config.yaml
        await app.initialize()    # 初始化所有组件（加载模型等）
        await app.run()           # 开始监听热键 + 语音识别
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.device_manager: Optional[AudioDeviceManager] = None
        self.capture: Optional[AudioCapture] = None
        self.engine = None
        self.pipeline: Optional[ProcessorPipeline] = None
        self.hotkey: Optional[HotkeyListener] = None
        self._recording_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """初始化所有组件"""
        # 日志
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

        logger.info("=== mutimodel-voice-plugin initializing ===")

        # 1. 音频设备
        self.device_manager = AudioDeviceManager(
            preferred_keywords=self.config.audio.preferred_devices
        )
        device = self.device_manager.select_best_device()
        logger.info(f"Audio device: {device}")

        self.capture = AudioCapture(
            device=device,
            config=AudioConfig(
                sample_rate=self.config.audio.sample_rate,
                channels=self.config.audio.channels,
                chunk_duration_ms=self.config.audio.chunk_duration_ms,
            ),
            device_manager=self.device_manager,
        )

        # 2. ASR 引擎（确保注册了 sensevoice）
        self._register_engines()
        self.engine = EngineRegistry.create(
            self.config.asr.engine,
            model=self.config.asr.model,
            device=self.config.asr.device,
            language=self.config.asr.language,
        )
        await self.engine.initialize()
        logger.info(f"ASR engine: {self.engine.name}")

        # 3. 后处理 Pipeline
        self.pipeline = self._build_pipeline()
        logger.info(f"Pipeline: {self.pipeline.list_processors()}")

        # 4. 热键
        self.hotkey = HotkeyListener(
            config=HotkeyConfig(
                key=self.config.hotkey.key,
                mode=HotkeyMode(self.config.hotkey.mode),
            ),
            on_start=self._on_start_recording,
            on_stop=self._on_stop_recording,
        )

        logger.info("=== Initialization complete ===")
        logger.info(f"Press [{self.config.hotkey.key.upper()}] to start/stop recording")

    def _register_engines(self) -> None:
        """确保所有引擎模块被导入（触发自动注册）"""
        # 导入即注册
        from .engines import sensevoice_engine  # noqa: F401
        from .engines import doubao_asr  # noqa: F401
        from .engines import whisper_engine  # noqa: F401

    def _build_pipeline(self) -> ProcessorPipeline:
        """根据配置构建后处理 Pipeline"""
        pipeline = ProcessorPipeline()
        enabled = self.config.processors.pipeline

        if "filler_filter" in enabled:
            pipeline.add(FillerFilterProcessor())

        if "dictionary_replace" in enabled:
            # 加载词典
            dict_mgr = DictionaryManager(self.config.processors.dictionary_dir)
            dict_mgr.create_default_dictionary()
            for dict_file in self.config.processors.dictionary_files:
                dict_path = dict_mgr.get_dict_path(dict_file)
                if dict_path.exists():
                    pipeline.add(DictionaryReplaceProcessor(dict_path=str(dict_path)))

        if "llm_polish" in enabled:
            pipeline.add(
                LLMPolishProcessor(
                    config=LLMPolishConfig(
                        api_key=self.config.processors.llm_api_key,
                        base_url=self.config.processors.llm_base_url,
                        model=self.config.processors.llm_model,
                        enabled=self.config.processors.llm_enabled,
                    )
                )
            )

        return pipeline

    async def run(self) -> None:
        """启动应用主循环"""
        await self.hotkey.start()

        # 保持运行
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.shutdown()

    def _on_start_recording(self) -> None:
        """热键触发：开始录音"""
        logger.info("🎙️ Recording started")
        self._recording_task = asyncio.ensure_future(self._record_and_recognize())

    def _on_stop_recording(self) -> None:
        """热键触发：停止录音"""
        logger.info("⏹️ Recording stopped")
        if self.capture:
            self.capture.stop()

    async def _record_and_recognize(self) -> None:
        """录音 → ASR → 后处理 → 输出"""
        try:
            async for result in self.engine.recognize_stream(self.capture.stream()):
                if result.text.strip():
                    # 后处理
                    processed = await self.pipeline.run(
                        text=result.text,
                        language=result.language,
                        metadata={
                            "is_final": result.is_final,
                            "confidence": result.confidence,
                        },
                    )

                    if result.is_final:
                        self._output_text(processed.text)
                    else:
                        self._output_partial(processed.text)

        except Exception as e:
            logger.error(f"Recognition error: {e}")

    def _output_text(self, text: str) -> None:
        """输出最终文本（后续可以改为剪贴板粘贴、模拟键盘输入等）"""
        print(f"\n✅ {text}")

    def _output_partial(self, text: str) -> None:
        """输出中间结果"""
        sys.stdout.write(f"\r⏳ {text}")
        sys.stdout.flush()

    async def shutdown(self) -> None:
        """关闭所有组件"""
        logger.info("Shutting down...")
        if self.hotkey:
            self.hotkey.stop()
        if self.capture:
            self.capture.stop()
        if self.engine:
            await self.engine.shutdown()
