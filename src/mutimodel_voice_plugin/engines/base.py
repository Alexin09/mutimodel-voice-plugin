"""
ASR 引擎抽象基类 — 所有 ASR 后端必须实现此接口

设计理念：
- 流式优先：feed() 喂入音频块，recognize_stream() 输出文字流
- 同时支持整段识别 recognize() 用于离线场景
- 引擎无状态化：每次会话创建新的 session
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional


@dataclass
class ASRResult:
    """ASR 识别结果"""

    text: str  # 识别出的文字
    is_final: bool = False  # 是否为最终结果（vs 中间结果）
    confidence: float = 1.0  # 置信度 0-1
    start_time: Optional[float] = None  # 音频起始时间（秒）
    end_time: Optional[float] = None  # 音频结束时间（秒）
    language: Optional[str] = None  # 检测到的语言
    raw: dict = field(default_factory=dict)  # 原始 API 返回

    def __str__(self) -> str:
        status = "✓" if self.is_final else "…"
        return f"[{status}] {self.text}"


class BaseASREngine(abc.ABC):
    """
    ASR 引擎抽象基类

    所有 ASR 后端（豆包、Whisper、FunASR、Google STT...）都要实现这个接口。

    Lifecycle:
        engine = DoubaoEngine(config)
        await engine.initialize()

        # 流式识别
        async for result in engine.recognize_stream(audio_chunks):
            print(result)

        # 或整段识别
        result = await engine.recognize(audio_bytes)

        await engine.shutdown()
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """引擎名称，如 'doubao', 'whisper', 'funasr'"""
        ...

    @property
    def is_local(self) -> bool:
        """是否为本地引擎（无需网络）"""
        return False

    @property
    def supports_streaming(self) -> bool:
        """是否支持流式识别"""
        return True

    async def initialize(self) -> None:
        """初始化引擎（加载模型、建立连接等）"""
        pass

    async def shutdown(self) -> None:
        """关闭引擎，释放资源"""
        pass

    @abc.abstractmethod
    async def recognize_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[ASRResult, None]:
        """
        流式识别：持续接收音频块，持续输出识别结果

        Args:
            audio_stream: 异步音频块生成器

        Yields:
            ASRResult: 识别结果（包含中间结果和最终结果）
        """
        ...

    async def recognize(self, audio_data: bytes) -> ASRResult:
        """
        整段识别：一次性处理完整音频

        Args:
            audio_data: 完整的 PCM 音频数据

        Returns:
            ASRResult: 最终识别结果
        """
        raise NotImplementedError(f"{self.name} does not support batch recognition")
