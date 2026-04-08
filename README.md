<div align="center">

# 🎙️ mutimodel-voice-plugin

**Plug-and-play multi-model voice recognition pipeline with intelligent post-processing**

可插拔多模型语音识别 + 智能后处理 Pipeline

[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#-quick-start)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](#-what-is-this) · [中文](#-这是什么)

</div>

---

## 🤔 What is this?

You talk into a mic. The text that comes out the other side is **clean, accurate, and ready to use**.

```
You say:    "呃那个就是说我们下周三讨论一下欧克二的皮皮迪"

You get:    "我们下周三讨论一下 OKR 的 PPT。"
```

**mutimodel-voice-plugin** is a pure-Python voice recognition pipeline that chains together:

1. **Audio Capture** — auto-detects your mic (DJI Mic, USB, Bluetooth, whatever)
2. **ASR Engine** — swappable: SenseVoice-Small (default, local) / Doubao (cloud) / Whisper (local)
3. **Post-Processing** — filler word removal → custom dictionary → LLM polish

Everything runs **locally by default**. Your voice never leaves your machine.

## 🤔 这是什么？

你对着麦克风说话，出来的文字**干净、准确、可以直接用**。

这是一个纯 Python 语音识别流水线，把三件事串起来：

1. **音频捕获** — 自动识别你的麦克风（DJI Mic / USB / 蓝牙）
2. **ASR 引擎** — 可切换：SenseVoice-Small（默认，本地）/ 豆包（云端）/ Whisper（本地）
3. **后处理** — 口语过滤 → 词典替换 → LLM 润色

默认**全部本地运行**，你的语音数据不出你的电脑。

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🧠 SenseVoice-Small (Default)
Single model handles ASR + VAD + punctuation.
~450MB, 50+ languages, blazing fast.
No need for 3 separate models like Paraformer.

</td>
<td width="50%">

### 🔌 Plug-and-Play Engines
Switch ASR backends with one config line.
`sensevoice` → `doubao` → `whisper`
Add your own engine in ~50 lines of code.

</td>
</tr>
<tr>
<td>

### 🧹 Smart Post-Processing
Removes "um", "uh", "那个", "就是说".
Custom dictionary for your jargon.
Optional LLM polish (any OpenAI-compatible API).

</td>
<td>

### 🔒 Privacy First
SenseVoice runs 100% local.
No cloud, no API calls, no data upload.
Your voice stays on your machine.

</td>
</tr>
<tr>
<td>

### 📖 Hot-Reload Dictionary
Edit `dictionaries/default.yaml` → changes take effect immediately.
No restart needed. Add your own terms on the fly.

</td>
<td>

### ⌨️ Global Hotkey
Press `F2` to start/stop recording.
Push-to-Talk or Toggle mode.
Works system-wide.

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 mutimodel-voice-plugin                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🎤 Audio Capture    🧠 ASR Engine     📝 Post-Process  │
│  ┌─────────────┐    ┌─────────────┐   ┌─────────────┐  │
│  │ DJI Mic     │───▶│ SenseVoice  │──▶│ Filler Cut  │  │
│  │ USB Mic     │    │ Doubao      │   │ Dictionary  │  │
│  │ Bluetooth   │    │ Whisper     │   │ LLM Polish  │  │
│  │ Audio File  │    │ (Pluggable) │   │ (Pipeline)  │  │
│  └─────────────┘    └─────────────┘   └─────────────┘  │
│                                                         │
│  ⚙️  config.yaml  │  📖 dictionaries/  │  ⌨️  hotkey   │
└─────────────────────────────────────────────────────────┘
          │                                    │
     CLI: mvplugin                      Python Library
```

---

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/Alexin09/mutimodel-voice-plugin.git
cd mutimodel-voice-plugin

# Core + SenseVoice engine + hotkey
pip install -e ".[sensevoice,hotkey]"

# (Optional) Add LLM post-processing
pip install -e ".[all]"
```

### 2. Download SenseVoice-Small Model (~450MB)

```bash
# Auto-download from ModelScope
mvplugin download-model

# Or manually:
python scripts/download_model.py
```

> 📦 Model source: [ModelScope](https://modelscope.cn/models/iic/SenseVoiceSmall) · [HuggingFace](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)
>
> Downloaded to: `~/.cache/modelscope/hub/iic/SenseVoiceSmall/`

### 3. Run

```bash
# Start voice recognition (press F2 to toggle recording)
mvplugin run

# Or with options
mvplugin run --engine sensevoice --device mps --hotkey f2
```

That's it. Plug in your mic, press F2, start talking.

---

## 📋 CLI Commands

```bash
mvplugin run                          # Start voice recognition
mvplugin run --engine whisper         # Use Whisper instead
mvplugin run --config my_config.yaml  # Custom config file

mvplugin devices                      # List audio input devices
mvplugin download-model               # Download SenseVoice-Small

mvplugin dict list                    # List all dictionaries
mvplugin dict add "欧克二" "OKR"       # Add replacement rule

mvplugin test recording.wav           # Test recognition on a file
```

---

## ⚙️ Configuration

Edit `configs/config.yaml`:

```yaml
# ASR Engine
asr:
  engine: sensevoice          # sensevoice / doubao / whisper
  model: iic/SenseVoiceSmall
  device: auto                # auto / cpu / cuda / mps

# Post-Processing Pipeline (executed in order)
processors:
  pipeline:
    - filler_filter           # Remove "um", "那个", etc.
    - dictionary_replace      # Custom term replacement
    - llm_polish              # LLM refinement (optional)

  # LLM settings (any OpenAI-compatible API)
  llm_enabled: false
  llm_api_key: ""             # Or: export MVPLUGIN_LLM_API_KEY=sk-xxx
  llm_base_url: "https://api.openai.com/v1"
  llm_model: "gpt-4o-mini"

# Hotkey
hotkey:
  key: f2
  mode: toggle                # toggle / push_to_talk
```

### Environment Variables

All config values can be overridden:

```bash
export MVPLUGIN_ASR_ENGINE=whisper
export MVPLUGIN_ASR_DEVICE=mps
export MVPLUGIN_LLM_API_KEY=sk-your-key
export MVPLUGIN_HOTKEY=f3
```

---

## 📖 Custom Dictionary

Edit `dictionaries/default.yaml` — changes apply immediately (hot-reload):

```yaml
replacements:
  - from: "欧克二"
    to: "OKR"
  - from: ["赛恩斯沃伊斯", "森斯沃伊斯"]    # Multiple variants
    to: "SenseVoice"
  - from: "re:皮{1,2}迪"                    # Regex support
    to: "PPT"
```

Or via CLI:

```bash
mvplugin dict add "你的术语" "正确写法"
```

---

## 🔌 Engine Comparison

| Engine | Local | Streaming | Speed | Chinese | Multi-lang | Model Size |
|--------|-------|-----------|-------|---------|------------|------------|
| **SenseVoice-Small** ⭐ | ✅ | Segmented | ⚡⚡⚡ | ⭐⭐⭐⭐ | 50+ langs | ~450MB |
| **Doubao 2.0** | ❌ Cloud | ✅ Real-time | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | CN+EN | — |
| **Whisper** | ✅ | Segmented | ⚡ | ⭐⭐⭐ | 99 langs | 75MB–3GB |

> **Why SenseVoice-Small as default?**
> Single model = ASR + VAD + punctuation. No need for 3 separate models.
> ~450MB footprint. Non-autoregressive = 50x faster than Whisper.

---

## 🧩 Use as a Python Library

```python
import asyncio
from mutimodel_voice_plugin.engines.sensevoice_engine import SenseVoiceEngine
from mutimodel_voice_plugin.processors.pipeline import ProcessorPipeline
from mutimodel_voice_plugin.processors.filler_filter import FillerFilterProcessor
from mutimodel_voice_plugin.processors.dictionary_replace import DictionaryReplaceProcessor

async def main():
    # 1. Initialize ASR engine
    engine = SenseVoiceEngine(model="iic/SenseVoiceSmall", device="mps")
    await engine.initialize()

    # 2. Build post-processing pipeline
    pipeline = ProcessorPipeline()
    pipeline.add(FillerFilterProcessor())
    pipeline.add(DictionaryReplaceProcessor(
        replacements={"欧克二": "OKR", "皮皮迪": "PPT"}
    ))

    # 3. Recognize from file
    with open("recording.wav", "rb") as f:
        audio_data = f.read()
    result = await engine.recognize(audio_data)

    # 4. Post-process
    processed = await pipeline.run(result.text)
    print(processed.text)

asyncio.run(main())
```

---

## 🆚 Comparison

| | **mutimodel-voice-plugin** | Wispr Flow | 蛐蛐 QuQu | 闪电说 |
|---|---|---|---|---|
| **Price** | ✅ Free & open source | $12/month | Free | Paid |
| **Privacy** | ✅ 100% local | Cloud | Local | Cloud |
| **Core Model** | SenseVoice-Small | Whisper | Paraformer-Large | Doubao |
| **Engine Swap** | ✅ Config one-liner | ❌ | ❌ | ❌ |
| **Interface** | CLI + Python lib | GUI | GUI (Electron) | GUI |
| **Target User** | Developers | General | General | General |
| **Custom Dictionary** | ✅ YAML hot-reload | ❌ | ❌ | ✅ Built-in |
| **LLM Post-process** | ✅ Any OpenAI API | ❌ | ✅ | Exploring |
| **Code Size** | Pure Python, ~2K LOC | — | Electron+Python | Closed |

---

## 🗺️ Roadmap

- [x] Core pipeline: Audio → ASR → Post-process → Output
- [x] SenseVoice-Small as default engine
- [x] Pluggable engine architecture (SenseVoice / Doubao / Whisper)
- [x] Filler word filter (Chinese + English)
- [x] Custom dictionary with hot-reload
- [x] LLM post-processing (OpenAI-compatible)
- [x] Global hotkey (F2, Toggle / Push-to-Talk)
- [x] CLI tool (`mvplugin`)
- [ ] Clipboard paste / keyboard simulation (type into any app)
- [ ] System tray with status indicator
- [ ] Real-time partial results display
- [ ] Audio file batch processing mode
- [ ] WebSocket API for third-party integration
- [ ] Electron/Tauri GUI wrapper
- [ ] PyPI package release

---

## 🙏 Acknowledgements

This project builds on top of amazing open-source work:

- **[FunAudioLLM/SenseVoice](https://github.com/FunAudioLLM/SenseVoice)** — The core ASR model. Multilingual voice understanding from Alibaba.
- **[FunASR](https://github.com/modelscope/FunASR)** — Industrial-grade speech recognition toolkit.
- **[蛐蛐 QuQu](https://github.com/yan5xu/ququ)** — Inspiration for the desktop voice input workflow.
- **[Wispr Flow](https://wispr.com)** — Inspiration for the "speak and it types" experience.

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/Alexin09/mutimodel-voice-plugin.git
cd mutimodel-voice-plugin
pip install -e ".[dev,all]"
pytest
```

---

## 📄 License

[Apache License 2.0](LICENSE) — use it however you want.

---

<div align="center">

**If this project helps you, give it a ⭐**

Built with 🎙️ by [Jon](https://github.com/Alexin09)

</div>
