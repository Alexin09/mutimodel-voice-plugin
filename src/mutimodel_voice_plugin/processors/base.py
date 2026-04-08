"""
后处理器抽象基类 — Pipeline 中的每一步都是一个 Processor

设计理念：
- 每个 Processor 做一件事（单一职责）
- 输入/输出统一为 ProcessorResult，可链式调用
- 支持 async，方便 LLM 调用等 IO 密集场景
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessorResult:
    """处理器的输入/输出"""

    text: str  # 当前文本
    original_text: str = ""  # ASR 原始文本（不可变，用于对比）
    language: Optional[str] = None  # 语言标识
    metadata: dict = field(default_factory=dict)  # 元数据透传（情绪、事件等）

    def __post_init__(self):
        if not self.original_text:
            self.original_text = self.text


class BaseProcessor(abc.ABC):
    """
    后处理器基类

    所有 Processor 必须实现 process() 方法。
    Pipeline 会按注册顺序依次调用每个 Processor。
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """处理器名称"""
        ...

    @property
    def enabled(self) -> bool:
        """是否启用（可通过配置动态开关）"""
        return True

    @abc.abstractmethod
    async def process(self, result: ProcessorResult) -> ProcessorResult:
        """
        处理文本

        Args:
            result: 上一步的处理结果

        Returns:
            ProcessorResult: 处理后的结果
        """
        ...
