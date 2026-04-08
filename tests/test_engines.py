"""ASR 引擎注册表测试"""

import pytest
from mutimodel_voice_plugin.engines.registry import EngineRegistry
from mutimodel_voice_plugin.engines.base import BaseASREngine


def test_registry_register_and_list():
    """测试引擎注册和列出"""
    # sensevoice/doubao/whisper 在 import 时自动注册
    from mutimodel_voice_plugin.engines import sensevoice_engine  # noqa: F401

    engines = EngineRegistry.list_engines()
    assert "sensevoice" in engines


def test_registry_create_sensevoice():
    """测试创建 SenseVoice 引擎实例"""
    from mutimodel_voice_plugin.engines import sensevoice_engine  # noqa: F401

    engine = EngineRegistry.create("sensevoice", model="iic/SenseVoiceSmall", device="cpu")
    assert engine.name == "sensevoice"
    assert engine.is_local is True


def test_registry_unknown_engine():
    """未知引擎应抛出 ValueError"""
    with pytest.raises(ValueError, match="Unknown ASR engine"):
        EngineRegistry.create("nonexistent_engine")
