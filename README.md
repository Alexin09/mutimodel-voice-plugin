<div align="center">

# 🎙️ mutimodel-voice-plugin

**Plug-and-play multi-model voice recognition pipeline with intelligent post-processing**

[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#-quick-start)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[中文文档](README_CN.md)**

</div>

---

## 🤔 What is this?

You talk into a mic. The text that comes out the other side is **clean, accurate, and ready to use**.

```
You say:    "So um basically like we need to uh discuss the OKR in next Wednesday's PPT"

You get:    "We need to discuss the OKR in next Wednesday's PPT."
```

> 🇨🇳 Works great for Chinese too — see [中文文档](README_CN.md) for Chinese examples.

**mutimodel-voice-plugin** is a pure-Python voice recognition pipeline that chains together:

1. **Audio Capture** — auto-detects your mic (DJI Mic, USB, Bluetooth, whatever)
2. **ASR Engine** — swappable: SenseVoice-Small (default, local) / Doubao (cloud) / Whisper (local)
3. **Post-Processing** — filler word removal → custom dictionary → LLM polish

Everything runs **locally by default**. Your voice never leaves your machine.

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

### 2. Download Model (~450MB)

```bash
mvplugin download-model
```

> 📦 Source: [ModelScope](https://modelscope.cn/models/iic/SenseVoiceSmall) · [HuggingFace](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)

### 3. Run

```bash
mvplugin run          # Press F2 to toggle recording
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
asr:
  engine: sensevoice          # sensevoice / doubao / whisper
  model: iic/SenseVoiceSmall
  device: auto                # auto / cpu / cuda / mps

processors:
  pipeline:
    - filler_filter           # Remove "um", "那个", etc.
    - dictionary_replace      # Custom term replacement
    - llm_polish              # LLM refinement (optional)

  llm_enabled: false
  llm_api_key: ""             # Or: export MVPLUGIN_LLM_API_KEY=sk-xxx
  llm_base_url: "https://api.openai.com/v1"
  llm_model: "gpt-4o-mini"

hotkey:
  key: f2
  mode: toggle                # toggle / push_to_talk
```

### Environment Variables

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

---

## 🔌 Engine Comparison

| Engine | Local | Streaming | Speed | Chinese | Multi-lang | Size |
|--------|-------|-----------|-------|---------|------------|------|
| **SenseVoice-Small** ⭐ | ✅ | Segmented | ⚡⚡⚡ | ⭐⭐⭐⭐ | 50+ langs | ~450MB |
| **Doubao 2.0** | ❌ Cloud | ✅ Real-time | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | CN+EN | — |
| **Whisper** | ✅ | Segmented | ⚡ | ⭐⭐⭐ | 99 langs | 75MB–3GB |

---

## 🧩 Use as Python Library

```python
import asyncio
from mutimodel_voice_plugin.engines.sensevoice_engine import SenseVoiceEngine
from mutimodel_voice_plugin.processors.pipeline import ProcessorPipeline
from mutimodel_voice_plugin.processors.filler_filter import FillerFilterProcessor
from mutimodel_voice_plugin.processors.dictionary_replace import DictionaryReplaceProcessor

async def main():
    engine = SenseVoiceEngine(model="iic/SenseVoiceSmall", device="mps")
    await engine.initialize()

    pipeline = ProcessorPipeline()
    pipeline.add(FillerFilterProcessor())
    pipeline.add(DictionaryReplaceProcessor(
        replacements={"欧克二": "OKR", "皮皮迪": "PPT"}
    ))

    with open("recording.wav", "rb") as f:
        result = await engine.recognize(f.read())

    processed = await pipeline.run(result.text)
    print(processed.text)

asyncio.run(main())
```

---

## 🆚 Comparison

| | **This Project** | Wispr Flow | QuQu | 闪电说 |
|---|---|---|---|---|
| **Price** | ✅ Free | $12/mo | Free | Paid |
| **Privacy** | ✅ Local | Cloud | Local | Cloud |
| **Model** | SenseVoice-Small | Whisper | Paraformer | Doubao |
| **Engine Swap** | ✅ One-liner | ❌ | ❌ | ❌ |
| **Interface** | CLI + Lib | GUI | GUI | GUI |
| **Dictionary** | ✅ Hot-reload | ❌ | ❌ | ✅ |
| **LLM Polish** | ✅ Any API | ❌ | ✅ | Exploring |

---

## 🗺️ Roadmap

- [x] Core pipeline: Audio → ASR → Post-process → Output
- [x] SenseVoice-Small / Doubao / Whisper engines
- [x] Filler filter + dictionary + LLM polish
- [x] Global hotkey + CLI tool
- [ ] Clipboard paste / keyboard simulation
- [ ] System tray with status indicator
- [ ] WebSocket API for integration
- [ ] GUI wrapper (Electron/Tauri)
- [ ] PyPI release

---

## 🙏 Acknowledgements

- **[FunAudioLLM/SenseVoice](https://github.com/FunAudioLLM/SenseVoice)** — Core ASR model
- **[FunASR](https://github.com/modelscope/FunASR)** — Speech recognition toolkit
- **[QuQu](https://github.com/yan5xu/ququ)** — Desktop voice workflow inspiration

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome!

## 📄 License

[Apache License 2.0](LICENSE)

---

<div align="center">

**If this helps you, give it a ⭐**

Built with 🎙️ by [Jon](https://github.com/Alexin09)

</div>
