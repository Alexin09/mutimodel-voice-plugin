"""
口语填充词过滤器

把"呃……那个……就是说我们下周三开会"变成"我们下周三开会"

支持中英文常见填充词，可通过配置扩展。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .base import BaseProcessor, ProcessorResult


@dataclass
class FillerFilterConfig:
    """填充词过滤配置"""

    # 中文填充词
    zh_fillers: list[str] = field(
        default_factory=lambda: [
            "嗯",
            "啊",
            "呃",
            "额",
            "哦",
            "噢",
            "那个",
            "这个",
            "就是",
            "就是说",
            "然后",
            "然后呢",
            "所以说",
            "怎么说呢",
            "反正",
            "其实",
            "对吧",
            "你知道吗",
            "我觉得吧",
            "怎么说",
            "说白了",
            "基本上",
            "差不多",
            "大概",
        ]
    )
    # 英文填充词
    en_fillers: list[str] = field(
        default_factory=lambda: [
            "uh",
            "um",
            "hmm",
            "ah",
            "oh",
            "like",
            "you know",
            "basically",
            "actually",
            "literally",
            "so",
            "I mean",
            "kind of",
            "sort of",
        ]
    )
    # 是否清理多余空白
    clean_whitespace: bool = True
    # 是否清理重复标点
    clean_punctuation: bool = True


class FillerFilterProcessor(BaseProcessor):
    """
    口语填充词过滤器

    策略：
    1. 正则匹配并移除填充词（注意上下文边界，避免误删）
    2. 清理多余空格和重复标点
    """

    def __init__(self, config: FillerFilterConfig | None = None):
        self.config = config or FillerFilterConfig()
        self._pattern = self._build_pattern()

    @property
    def name(self) -> str:
        return "filler_filter"

    def _build_pattern(self) -> re.Pattern:
        """构建匹配正则"""
        all_fillers = self.config.zh_fillers + self.config.en_fillers
        # 按长度降序排列，优先匹配长词（避免"就是说"被"就是"先匹配）
        all_fillers.sort(key=len, reverse=True)
        # 转义特殊字符
        escaped = [re.escape(f) for f in all_fillers]
        # 构建模式：填充词可能前后有标点或空格
        pattern = (
            r"(?:^|(?<=[\s，。！？,.\s]))(?:"
            + "|".join(escaped)
            + r")(?:[\s，。、,.\s]*)"
        )
        return re.compile(pattern, re.IGNORECASE)

    async def process(self, result: ProcessorResult) -> ProcessorResult:
        text = result.text

        # 1. 移除填充词
        text = self._pattern.sub("", text)

        # 2. 清理多余空白
        if self.config.clean_whitespace:
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

        # 3. 清理重复标点
        if self.config.clean_punctuation:
            text = re.sub(r"[，,]{2,}", "，", text)
            text = re.sub(r"[。.]{2,}", "。", text)
            text = re.sub(r"^[，,。.\s]+", "", text)  # 开头的标点

        result.text = text
        return result
