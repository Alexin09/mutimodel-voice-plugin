"""
引擎注册表 — 管理所有可用的 ASR 引擎

支持通过配置文件名字符串实例化引擎，实现真正的可插拔。
"""

from __future__ import annotations

import logging
from typing import Type

from .base import BaseASREngine

logger = logging.getLogger(__name__)


class EngineRegistry:
    """
    ASR 引擎注册表

    Usage:
        # 注册
        EngineRegistry.register("doubao", DoubaoEngine)
        EngineRegistry.register("whisper", WhisperEngine)

        # 通过配置名创建
        engine = EngineRegistry.create("doubao", api_key="xxx")
    """

    _engines: dict[str, Type[BaseASREngine]] = {}

    @classmethod
    def register(cls, name: str, engine_class: Type[BaseASREngine]) -> None:
        """注册一个 ASR 引擎"""
        cls._engines[name] = engine_class
        logger.info(f"Registered ASR engine: {name}")

    @classmethod
    def create(cls, name: str, **kwargs) -> BaseASREngine:
        """根据名称创建引擎实例"""
        if name not in cls._engines:
            available = ", ".join(cls._engines.keys())
            raise ValueError(f"Unknown ASR engine: '{name}'. Available: {available}")
        return cls._engines[name](**kwargs)

    @classmethod
    def list_engines(cls) -> list[str]:
        """列出所有已注册的引擎名称"""
        return list(cls._engines.keys())

    @classmethod
    def get(cls, name: str) -> Type[BaseASREngine]:
        """获取引擎类"""
        return cls._engines[name]
