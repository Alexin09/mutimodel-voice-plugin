"""
SenseVoice-Small 引擎 — FunAudioLLM 开源多语言语音理解模型

特点：
- 单模型集成 ASR + VAD + 标点（不需要像 Paraformer 那样三个模型配合）
- 50+ 语言支持，中英混排极强
- 额外能力：情绪识别、音频事件检测（笑声/掌声/哭声等）
- 非自回归架构，推理速度极快（比 Whisper 快 ~50x）
- 模型体积 ~450MB，适合本地部署

模型来源：
- ModelScope: https://modelscope.cn/models/iic/SenseVoiceSmall
- HuggingFace: https://huggingface.co/FunAudioLLM/SenseVoiceSmall
- GitHub: https://github.com/FunAudioLLM/SenseVoice
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

from .base import ASRResult, BaseASREngine
from .registry import EngineRegistry

logger = logging.getLogger(__name__)


@dataclass
class SenseVoiceConfig:
    """SenseVoice-Small 配置"""

    # 模型路径（本地路径或 ModelScope/HuggingFace ID）
    model: str = "iic/SenseVoiceSmall"
    # 推理设备
    device: str = "auto"  # auto / cpu / cuda / mps
    # 语言（None = 自动检测）
    language: Optional[str] = "zh"  # zh / en / ja / ko / yue / auto
    # 是否使用 FunASR 的流式接口
    use_streaming: bool = False  # SenseVoice 本身非流式，通过分段模拟
    # VAD 参数（SenseVoice 内置 VAD）
    vad_threshold: float = 0.5
    # 批量推理相关
    batch_size: int = 1
    # 分段参数（用于伪流式）
    segment_duration_s: float = 3.0  # 每段音频长度（秒）
    # 额外功能
    detect_emotion: bool = False  # 是否提取情绪标签
    detect_event: bool = False  # 是否提取音频事件（笑声/掌声等）


@dataclass
class SenseVoiceResult(ASRResult):
    """SenseVoice 扩展结果，包含情绪和事件信息"""

    emotion: Optional[str] = None  # 情绪标签: happy/sad/angry/neutral
    event: Optional[str] = None  # 音频事件: laughter/applause/crying/...


class SenseVoiceEngine(BaseASREngine):
    """
    SenseVoice-Small 本地 ASR 引擎

    通过 FunASR 框架加载 SenseVoice-Small 模型。
    单模型完成：语音识别 + VAD + 标点 + 情绪 + 事件检测。

    Usage:
        engine = SenseVoiceEngine(
            model="iic/SenseVoiceSmall",
            device="mps",  # Mac Apple Silicon
        )
        await engine.initialize()

        # 整段识别
        result = await engine.recognize(audio_bytes)
        print(result.text)
        print(result.emotion)  # "happy"

        # 伪流式
        async for result in engine.recognize_stream(audio_stream):
            print(result.text)
    """

    def __init__(self, **kwargs):
        self.config = SenseVoiceConfig(
            **{
                k: v
                for k, v in kwargs.items()
                if k in SenseVoiceConfig.__dataclass_fields__
            }
        )
        self._model = None

    @property
    def name(self) -> str:
        return "sensevoice"

    @property
    def is_local(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        # SenseVoice 本身非自回归，不支持真正的 token-level 流式
        # 但通过分段可以模拟低延迟的伪流式
        return False

    async def initialize(self) -> None:
        """加载 SenseVoice-Small 模型"""
        logger.info(f"Loading SenseVoice model: {self.config.model}")
        logger.info(f"Device: {self.config.device}")

        def _load():
            from funasr import AutoModel

            model_kwargs = {
                "model": self.config.model,
                "model_revision": "v2.0.4",
                "disable_update": True,
            }

            # 设备选择
            device = self.config.device
            if device == "auto":
                import torch

                if torch.cuda.is_available():
                    device = "cuda"
                elif (
                    hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
                ):
                    device = "mps"
                else:
                    device = "cpu"

            model_kwargs["device"] = device
            logger.info(f"Using device: {device}")

            return AutoModel(**model_kwargs)

        self._model = await asyncio.get_event_loop().run_in_executor(None, _load)
        logger.info("SenseVoice model loaded successfully")

    async def shutdown(self) -> None:
        """释放模型资源"""
        self._model = None
        logger.info("SenseVoice engine shut down")

    async def recognize(self, audio_data: bytes) -> SenseVoiceResult:
        """
        整段识别

        Args:
            audio_data: PCM 16-bit mono 16kHz 音频数据

        Returns:
            SenseVoiceResult: 识别结果（含文字、情绪、事件）
        """
        if self._model is None:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        def _infer():
            import numpy as np

            # bytes → numpy float32
            audio_np = (
                np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            )

            # SenseVoice 推理
            result = self._model.generate(
                input=audio_np,
                batch_size_s=300,  # 单次最大处理时长（秒）
                language=self.config.language,
            )
            return result

        raw_result = await asyncio.get_event_loop().run_in_executor(None, _infer)

        return self._parse_result(raw_result)

    async def recognize_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[SenseVoiceResult, None]:
        """
        伪流式识别：按 segment_duration_s 分段，每段独立识别

        对于 SenseVoice（非自回归模型），这是最实用的低延迟方案：
        - 累积 N 秒音频 → 送入模型 → 输出文字
        - 延迟 = segment_duration_s + 推理时间（通常 <200ms）
        """
        import numpy as np

        buffer = bytearray()
        segment_bytes = int(
            self.config.segment_duration_s * 16000 * 2  # 16kHz, 16-bit
        )

        async for chunk in audio_stream:
            buffer.extend(chunk)

            if len(buffer) >= segment_bytes:
                # 切出一段
                segment = bytes(buffer[:segment_bytes])
                buffer = bytearray(buffer[segment_bytes:])

                result = await self.recognize(segment)
                if result.text.strip():
                    yield result

        # 处理剩余音频（至少 0.5 秒才有意义）
        min_useful_bytes = int(0.5 * 16000 * 2)
        if len(buffer) >= min_useful_bytes:
            result = await self.recognize(bytes(buffer))
            if result.text.strip():
                result.is_final = True
                yield result

    def _parse_result(self, raw_result) -> SenseVoiceResult:
        """
        解析 FunASR / SenseVoice 的原始输出

        SenseVoice 的输出格式：
        - result[0]["text"]: 识别文字（可能包含情绪/事件标签）
        - 标签格式: <|emotion|>text 或 <|event|>text
        """
        if not raw_result or not raw_result[0].get("text"):
            return SenseVoiceResult(text="", is_final=True)

        raw_text = raw_result[0]["text"]
        text = raw_text
        emotion = None
        event = None

        # 解析特殊标签
        if self.config.detect_emotion or self.config.detect_event:
            text, emotion, event = self._extract_tags(raw_text)

        return SenseVoiceResult(
            text=text.strip(),
            is_final=True,
            confidence=raw_result[0].get("confidence", 1.0)
            if isinstance(raw_result[0], dict)
            else 1.0,
            language=self.config.language,
            raw={"funasr_output": raw_result},
            emotion=emotion,
            event=event,
        )

    @staticmethod
    def _extract_tags(text: str) -> tuple[str, Optional[str], Optional[str]]:
        """
        从 SenseVoice 输出中提取情绪和事件标签

        SenseVoice 会在文字前插入标签，格式如：
        <|HAPPY|><|Speech|>今天天气真好
        <|NEUTRAL|><|Laughter|>哈哈哈
        """
        import re

        emotion = None
        event = None
        clean_text = text

        # 提取情绪标签
        emotion_match = re.search(
            r"<\|(HAPPY|SAD|ANGRY|NEUTRAL|FEARFUL|DISGUSTED|SURPRISED)\|>",
            text,
            re.IGNORECASE,
        )
        if emotion_match:
            emotion = emotion_match.group(1).lower()

        # 提取事件标签
        event_match = re.search(
            r"<\|(Speech|Laughter|Applause|Crying|Music|BGM|Noise)\|>",
            text,
            re.IGNORECASE,
        )
        if event_match:
            event = event_match.group(1).lower()

        # 清除所有标签
        clean_text = re.sub(r"<\|[^|]+\|>", "", text)

        return clean_text, emotion, event


# 自动注册到引擎注册表
EngineRegistry.register("sensevoice", SenseVoiceEngine)
