"""
处理器 Pipeline — 将多个 Processor 串联执行

执行顺序（可通过 config 自定义）：
1. FillerFilter  — 去除口语填充词（嗯、啊、那个、就是说）
2. DictionaryReplace — 自定义词典替换（专业术语、人名、缩写）
3. LLMPolish — LLM 智能润色/纠错/结构化
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .base import BaseProcessor, ProcessorResult

logger = logging.getLogger(__name__)


class ProcessorPipeline:
    """
    后处理 Pipeline

    Usage:
        pipeline = ProcessorPipeline()
        pipeline.add(FillerFilterProcessor())
        pipeline.add(DictionaryReplaceProcessor(dict_path="my_dict.yaml"))
        pipeline.add(LLMPolishProcessor(api_key="xxx"))

        result = await pipeline.run("呃那个就是说我们周三开会讨论一下OKR")
        # → "我们周三开会讨论一下 OKR"
    """

    def __init__(self):
        self._processors: list[BaseProcessor] = []

    def add(self, processor: BaseProcessor) -> "ProcessorPipeline":
        """添加处理器到 Pipeline 末尾"""
        self._processors.append(processor)
        logger.info(f"Pipeline: added processor [{processor.name}]")
        return self  # 支持链式调用

    def remove(self, name: str) -> None:
        """按名称移除处理器"""
        self._processors = [p for p in self._processors if p.name != name]

    def list_processors(self) -> list[str]:
        """列出所有处理器名称"""
        return [f"{'✓' if p.enabled else '✗'} {p.name}" for p in self._processors]

    async def run(
        self,
        text: str,
        language: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ProcessorResult:
        """
        执行 Pipeline

        Args:
            text: ASR 识别出的原始文本
            language: 语言标识
            metadata: 额外元数据（情绪、事件等）

        Returns:
            ProcessorResult: 经过所有处理器处理后的最终结果
        """
        result = ProcessorResult(
            text=text,
            original_text=text,
            language=language,
            metadata=metadata or {},
        )

        for processor in self._processors:
            if not processor.enabled:
                logger.debug(f"Skipping disabled processor: {processor.name}")
                continue

            start = time.monotonic()
            try:
                result = await processor.process(result)
                elapsed = (time.monotonic() - start) * 1000
                logger.debug(
                    f"[{processor.name}] {elapsed:.1f}ms → {result.text[:50]}..."
                )
            except Exception as e:
                logger.error(f"Processor [{processor.name}] failed: {e}")
                # 某个处理器失败不影响整体 Pipeline，跳过继续

        return result
