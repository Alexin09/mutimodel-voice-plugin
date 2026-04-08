"""
词典管理器 — 管理多个自定义词典文件

支持：
- 多词典叠加（全局词典 + 场景词典）
- 热加载（文件改了立刻生效）
- CLI 命令行管理（添加/删除/列出规则）
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_DICT_DIR = Path(__file__).parent.parent.parent.parent / "dictionaries"


class DictionaryManager:
    """
    词典管理器

    Usage:
        mgr = DictionaryManager(dict_dir="./dictionaries")
        mgr.list_dictionaries()  # ["default.yaml", "tech.yaml"]
        mgr.add_rule("default", "欧克二", "OKR")
        mgr.save()
    """

    def __init__(self, dict_dir: Optional[str] = None):
        self.dict_dir = Path(dict_dir) if dict_dir else DEFAULT_DICT_DIR
        self.dict_dir.mkdir(parents=True, exist_ok=True)

    def list_dictionaries(self) -> list[str]:
        """列出所有词典文件"""
        return [f.name for f in self.dict_dir.glob("*.yaml")]

    def get_dict_path(self, name: str) -> Path:
        """获取词典文件路径"""
        if not name.endswith(".yaml"):
            name = f"{name}.yaml"
        return self.dict_dir / name

    def load_dictionary(self, name: str) -> dict:
        """加载词典内容"""
        import yaml

        path = self.get_dict_path(name)
        if not path.exists():
            return {"replacements": []}

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"replacements": []}

    def save_dictionary(self, name: str, data: dict) -> None:
        """保存词典"""
        import yaml

        path = self.get_dict_path(name)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        logger.info(f"Dictionary saved: {path}")

    def add_rule(self, dict_name: str, source: str | list[str], target: str) -> None:
        """添加替换规则"""
        data = self.load_dictionary(dict_name)
        data["replacements"].append(
            {
                "from": source,
                "to": target,
            }
        )
        self.save_dictionary(dict_name, data)
        logger.info(f"Added rule: {source} → {target}")

    def remove_rule(self, dict_name: str, target: str) -> bool:
        """按目标词删除规则"""
        data = self.load_dictionary(dict_name)
        original_len = len(data["replacements"])
        data["replacements"] = [r for r in data["replacements"] if r["to"] != target]
        if len(data["replacements"]) < original_len:
            self.save_dictionary(dict_name, data)
            return True
        return False

    def create_default_dictionary(self) -> None:
        """创建默认词典（常见 ASR 误识别）"""
        default_path = self.get_dict_path("default")
        if default_path.exists():
            return

        default_data = {
            "replacements": [
                {"from": "欧克二", "to": "OKR"},
                {"from": "皮皮迪", "to": "PPT"},
                {"from": ["艾皮爱", "API接口"], "to": "API"},
                {"from": "吉特", "to": "Git"},
                {"from": "吉特哈布", "to": "GitHub"},
                {"from": ["赛恩斯沃伊斯", "森斯沃伊斯"], "to": "SenseVoice"},
                {"from": "大疆麦克", "to": "DJI Mic"},
            ]
        }
        self.save_dictionary("default", default_data)
        logger.info(f"Created default dictionary: {default_path}")
