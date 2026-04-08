"""
自定义词典替换处理器

将 ASR 常见误识别词替换为正确词汇。
适用于：专业术语、人名、产品名、缩写等。

词典格式（YAML）:
    replacements:
      - from: "欧克二"
        to: "OKR"
      - from: "皮皮迪"
        to: "PPT"
      - from: ["赛恩斯沃伊斯", "森斯沃伊斯"]
        to: "SenseVoice"
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .base import BaseProcessor, ProcessorResult

logger = logging.getLogger(__name__)


class DictionaryReplaceProcessor(BaseProcessor):
    """
    词典替换处理器

    支持：
    - YAML 词典文件
    - 一对多映射（多个错误写法 → 同一个正确词）
    - 热加载（文件修改后自动重新读取）
    - 正则模式匹配
    """

    def __init__(
        self,
        dict_path: Optional[str] = None,
        replacements: Optional[dict[str, str]] = None,
    ):
        """
        Args:
            dict_path: YAML 词典文件路径
            replacements: 直接传入替换映射 {"错误词": "正确词"}
        """
        self._dict_path = Path(dict_path) if dict_path else None
        self._replacements: list[tuple[re.Pattern, str]] = []
        self._file_mtime: float = 0

        if replacements:
            self._load_from_dict(replacements)

        if self._dict_path:
            self._load_from_file()

    @property
    def name(self) -> str:
        return "dictionary_replace"

    def _load_from_file(self) -> None:
        """从 YAML 文件加载词典"""
        if not self._dict_path or not self._dict_path.exists():
            logger.warning(f"Dictionary file not found: {self._dict_path}")
            return

        import yaml

        mtime = self._dict_path.stat().st_mtime
        if mtime == self._file_mtime:
            return  # 文件未变

        with open(self._dict_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._replacements.clear()

        for item in data.get("replacements", []):
            target = item["to"]
            sources = item["from"]
            if isinstance(sources, str):
                sources = [sources]

            for src in sources:
                # 支持正则语法（以 "re:" 开头）
                if src.startswith("re:"):
                    pattern = re.compile(src[3:], re.IGNORECASE)
                else:
                    pattern = re.compile(re.escape(src), re.IGNORECASE)
                self._replacements.append((pattern, target))

        self._file_mtime = mtime
        logger.info(
            f"Loaded {len(self._replacements)} dictionary rules from {self._dict_path}"
        )

    def _load_from_dict(self, replacements: dict[str, str]) -> None:
        """从字典加载"""
        for src, target in replacements.items():
            pattern = re.compile(re.escape(src), re.IGNORECASE)
            self._replacements.append((pattern, target))

    async def process(self, result: ProcessorResult) -> ProcessorResult:
        # 热加载检查
        if self._dict_path:
            self._load_from_file()

        text = result.text
        for pattern, replacement in self._replacements:
            text = pattern.sub(replacement, text)

        result.text = text
        return result

    def add_rule(self, source: str, target: str) -> None:
        """动态添加替换规则"""
        pattern = re.compile(re.escape(source), re.IGNORECASE)
        self._replacements.append((pattern, target))

    @property
    def rule_count(self) -> int:
        return len(self._replacements)
