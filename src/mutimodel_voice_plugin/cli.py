"""
CLI 入口 — 命令行工具

Commands:
    mvplugin run              # 启动语音识别（默认）
    mvplugin run --engine sensevoice --device mps
    mvplugin devices          # 列出音频设备
    mvplugin dict list        # 列出词典
    mvplugin dict add "欧克二" "OKR"
    mvplugin download-model   # 下载 SenseVoice-Small 模型
    mvplugin test             # 从文件测试识别
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="mvplugin",
        description="mutimodel-voice-plugin: 多模型语音识别 + 智能后处理",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- run ---
    run_parser = subparsers.add_parser("run", help="启动语音识别")
    run_parser.add_argument("--config", "-c", help="配置文件路径")
    run_parser.add_argument(
        "--engine", "-e", choices=["sensevoice", "doubao", "whisper"]
    )
    run_parser.add_argument("--device", "-d", help="推理设备 (auto/cpu/cuda/mps)")
    run_parser.add_argument("--hotkey", help="快捷键 (default: f2)")

    # --- devices ---
    subparsers.add_parser("devices", help="列出音频输入设备")

    # --- dict ---
    dict_parser = subparsers.add_parser("dict", help="词典管理")
    dict_sub = dict_parser.add_subparsers(dest="dict_cmd")
    dict_sub.add_parser("list", help="列出词典")
    dict_add = dict_sub.add_parser("add", help="添加替换规则")
    dict_add.add_argument("source", help="源词（ASR 误识别）")
    dict_add.add_argument("target", help="目标词（正确写法）")
    dict_add.add_argument("--dict", default="default", help="词典名称")

    # --- download-model ---
    dl_parser = subparsers.add_parser("download-model", help="下载 ASR 模型")
    dl_parser.add_argument("--model", default="iic/SenseVoiceSmall", help="模型 ID")

    # --- test ---
    test_parser = subparsers.add_parser("test", help="从音频文件测试识别")
    test_parser.add_argument("file", help="音频文件路径 (wav/mp3)")
    test_parser.add_argument("--engine", "-e", default="sensevoice")

    args = parser.parse_args()

    if args.command == "run" or args.command is None:
        _cmd_run(args)
    elif args.command == "devices":
        _cmd_devices()
    elif args.command == "dict":
        _cmd_dict(args)
    elif args.command == "download-model":
        _cmd_download(args)
    elif args.command == "test":
        _cmd_test(args)
    else:
        parser.print_help()


def _cmd_run(args):
    """启动主应用"""
    from .config import load_config
    from .app import VoiceApp

    config = load_config(getattr(args, "config", None))

    # CLI 参数覆盖
    if hasattr(args, "engine") and args.engine:
        config.asr.engine = args.engine
    if hasattr(args, "device") and args.device:
        config.asr.device = args.device
    if hasattr(args, "hotkey") and args.hotkey:
        config.hotkey.key = args.hotkey

    app = VoiceApp(config=config)

    async def _run():
        await app.initialize()
        await app.run()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nBye!")


def _cmd_devices():
    """列出音频设备"""
    from .audio.device import AudioDeviceManager

    mgr = AudioDeviceManager()
    devices = mgr.list_devices()

    if not devices:
        print("No audio input devices found.")
        return

    print(f"\n🎤 Found {len(devices)} audio input devices:\n")
    for d in devices:
        print(f"  {d}")
    print()


def _cmd_dict(args):
    """词典管理"""
    from .dictionary.manager import DictionaryManager

    mgr = DictionaryManager()

    if args.dict_cmd == "list":
        dicts = mgr.list_dictionaries()
        if not dicts:
            print("No dictionaries found. Run 'mvplugin run' to create default.")
            return
        for d in dicts:
            data = mgr.load_dictionary(d)
            count = len(data.get("replacements", []))
            print(f"  📖 {d} ({count} rules)")

    elif args.dict_cmd == "add":
        mgr.add_rule(args.dict, args.source, args.target)
        print(f"✅ Added: {args.source} → {args.target} (dict: {args.dict})")

    else:
        print("Usage: mvplugin dict [list|add]")


def _cmd_download(args):
    """下载模型"""
    print(f"Downloading model: {args.model}")
    print("This may take a few minutes...\n")

    try:
        from funasr import AutoModel

        AutoModel(model=args.model, model_revision="v2.0.4")
        print(f"\n✅ Model downloaded: {args.model}")
    except ImportError:
        print("❌ funasr not installed. Run: pip install funasr")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Download failed: {e}")
        sys.exit(1)


def _cmd_test(args):
    """测试识别"""

    async def _run_test():
        from .config import load_config
        from .engines.registry import EngineRegistry

        # 注册引擎
        from .engines import sensevoice_engine  # noqa: F401
        from .engines import whisper_engine  # noqa: F401

        config = load_config()
        config.asr.engine = args.engine

        engine = EngineRegistry.create(
            args.engine,
            model=config.asr.model,
            device=config.asr.device,
            language=config.asr.language,
        )
        await engine.initialize()

        # 读取音频文件
        import soundfile as sf
        import numpy as np

        data, sr = sf.read(args.file, dtype="int16")
        if sr != 16000:
            print(f"Warning: file sample rate is {sr}, resampling to 16000")

        audio_bytes = data.tobytes()
        result = await engine.recognize(audio_bytes)

        print(f"\n🎙️ File: {args.file}")
        print(f"🔤 Result: {result.text}")
        if hasattr(result, "emotion") and result.emotion:
            print(f"😊 Emotion: {result.emotion}")

    asyncio.run(_run_test())


if __name__ == "__main__":
    main()
