#!/usr/bin/env python3
"""
下载 SenseVoice-Small 模型

模型来源：
- ModelScope: https://modelscope.cn/models/iic/SenseVoiceSmall
- HuggingFace: https://huggingface.co/FunAudioLLM/SenseVoiceSmall

用法：
    python scripts/download_model.py
    python scripts/download_model.py --model iic/SenseVoiceSmall
    python scripts/download_model.py --source huggingface

模型将下载到 ~/.cache/modelscope/ 或 ~/.cache/huggingface/
"""

import argparse
import sys
import time


def download_sensevoice(model_id: str = "iic/SenseVoiceSmall", source: str = "modelscope"):
    """下载 SenseVoice-Small 模型"""
    print(f"📦 Model: {model_id}")
    print(f"📡 Source: {source}")
    print(f"⏳ Downloading... (this may take a few minutes)\n")

    start = time.time()

    try:
        from funasr import AutoModel

        model = AutoModel(
            model=model_id,
            model_revision="v2.0.4",
            disable_update=True,
        )

        elapsed = time.time() - start
        print(f"\n✅ Download complete! ({elapsed:.1f}s)")
        print(f"📁 Model cached at: ~/.cache/modelscope/hub/{model_id.replace('/', '--')}")
        return True

    except ImportError:
        print("❌ Error: funasr not installed")
        print("   Run: pip install 'mutimodel-voice-plugin[sensevoice]'")
        return False

    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download ASR models")
    parser.add_argument(
        "--model", default="iic/SenseVoiceSmall", help="Model ID (default: iic/SenseVoiceSmall)"
    )
    parser.add_argument(
        "--source",
        default="modelscope",
        choices=["modelscope", "huggingface"],
        help="Download source",
    )
    args = parser.parse_args()

    # 根据来源调整 model_id
    model_id = args.model
    if args.source == "huggingface" and not model_id.startswith("FunAudioLLM"):
        model_id = "FunAudioLLM/SenseVoiceSmall"

    success = download_sensevoice(model_id, args.source)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
