"""
配置管理 — 加载和验证 config.yaml

支持：
- YAML 配置文件
- 环境变量覆盖（MVPLUGIN_ASR_ENGINE=sensevoice）
- 命令行参数覆盖
- 默认值回退
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "configs" / "config.yaml"


@dataclass
class AudioSettings:
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 100
    preferred_devices: list[str] = field(default_factory=lambda: ["DJI"])


@dataclass
class ASRSettings:
    engine: str = "sensevoice"  # sensevoice / doubao / whisper
    model: str = "iic/SenseVoiceSmall"
    device: str = "auto"  # auto / cpu / cuda / mps
    language: str = "zh"


@dataclass
class ProcessorSettings:
    # 启用的处理器列表（按顺序执行）
    pipeline: list[str] = field(
        default_factory=lambda: [
            "filler_filter",
            "dictionary_replace",
            "llm_polish",
        ]
    )
    # 词典配置
    dictionary_dir: str = "dictionaries"
    dictionary_files: list[str] = field(default_factory=lambda: ["default.yaml"])
    # LLM 配置
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_enabled: bool = False  # 默认关闭，需要用户配 API Key


@dataclass
class HotkeySettings:
    key: str = "f2"
    mode: str = "toggle"  # toggle / push_to_talk


@dataclass
class AppConfig:
    """应用总配置"""

    audio: AudioSettings = field(default_factory=AudioSettings)
    asr: ASRSettings = field(default_factory=ASRSettings)
    processors: ProcessorSettings = field(default_factory=ProcessorSettings)
    hotkey: HotkeySettings = field(default_factory=HotkeySettings)
    # 日志
    log_level: str = "INFO"


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    加载配置

    优先级：环境变量 > 配置文件 > 默认值
    """
    config = AppConfig()

    # 1. 从文件加载
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if path.exists():
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = _merge_config(config, data)
        logger.info(f"Config loaded from: {path}")
    else:
        logger.info(f"No config file found at {path}, using defaults")

    # 2. 环境变量覆盖
    env_overrides = {
        "MVPLUGIN_ASR_ENGINE": ("asr", "engine"),
        "MVPLUGIN_ASR_MODEL": ("asr", "model"),
        "MVPLUGIN_ASR_DEVICE": ("asr", "device"),
        "MVPLUGIN_LLM_API_KEY": ("processors", "llm_api_key"),
        "MVPLUGIN_LLM_BASE_URL": ("processors", "llm_base_url"),
        "MVPLUGIN_LLM_MODEL": ("processors", "llm_model"),
        "MVPLUGIN_HOTKEY": ("hotkey", "key"),
        "MVPLUGIN_LOG_LEVEL": (None, "log_level"),
    }

    for env_key, (section, field_name) in env_overrides.items():
        value = os.environ.get(env_key)
        if value:
            if section:
                setattr(getattr(config, section), field_name, value)
            else:
                setattr(config, field_name, value)
            logger.debug(f"Config override from env: {env_key}={value}")

    return config


def _merge_config(config: AppConfig, data: dict) -> AppConfig:
    """将 YAML dict 合并到 AppConfig"""
    if "audio" in data:
        for k, v in data["audio"].items():
            if hasattr(config.audio, k):
                setattr(config.audio, k, v)

    if "asr" in data:
        for k, v in data["asr"].items():
            if hasattr(config.asr, k):
                setattr(config.asr, k, v)

    if "processors" in data:
        for k, v in data["processors"].items():
            if hasattr(config.processors, k):
                setattr(config.processors, k, v)

    if "hotkey" in data:
        for k, v in data["hotkey"].items():
            if hasattr(config.hotkey, k):
                setattr(config.hotkey, k, v)

    if "log_level" in data:
        config.log_level = data["log_level"]

    return config
