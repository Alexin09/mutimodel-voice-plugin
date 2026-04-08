<div align="center">

# 🎙️ mutimodel-voice-plugin

**可插拔多模型语音识别 + 智能后处理 Pipeline**

[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#-快速开始)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

<a href="README.md">🌐 English</a> &nbsp;|&nbsp; <a href="README_CN.md">🇨🇳 简体中文</a>

</div>

---

## 💡 一句话说明

你对着麦克风说话，出来的文字**干净、准确、直接能用**。

```
你说：  "呃那个就是说我们下周三讨论一下欧克二的皮皮迪"
你得到：  "我们下周三讨论一下 OKR 的 PPT。"
```

---

## 🎯 为什么做这个？

| 现有方案 | 问题 |
|---------|------|
| **闪电说** | 闭源付费，被供应商锁定 |
| **蛐蛐 QuQu** | Electron 太重，Paraformer 需要三个模型配合 |
| **Wispr Flow** | $12/月订阅，数据上云，中文一般 |
| **系统自带语音输入** | 精度差，没有后处理，专业术语全错 |

**本项目的解法：**

- ✅ 纯 Python，轻量可嵌入
- ✅ SenseVoice-Small 单模型搞定一切（ASR + VAD + 标点），~450MB
- ✅ 引擎可插拔，config 改一行就能换
- ✅ 智能后处理：口语过滤 → 自定义词典 → LLM 润色
- ✅ 100% 本地运行，语音数据不出你的电脑

---

## 🏗️ 工作流程

```
🎤 DJI Mic / 任意麦克风
    │
    ▼
📡 音频捕获（自动设备发现，16kHz PCM）
    │
    ▼
🧠 ASR 引擎（可切换）
    ├── SenseVoice-Small ⭐ 默认，本地，50+语言
    ├── 豆包流式 ASR 2.0     云端，极低延迟
    └── Whisper               本地，99语言
    │
    ▼
📝 后处理 Pipeline（按顺序执行）
    ├── 1. 口语过滤     "呃那个就是说" → 删除
    ├── 2. 词典替换     "欧克二" → "OKR"
    └── 3. LLM 润色     上下文纠错 + 结构化（可选）
    │
    ▼
✅ 干净的文字输出
```

---

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/Alexin09/mutimodel-voice-plugin.git
cd mutimodel-voice-plugin

# 核心 + SenseVoice + 快捷键
pip install -e ".[sensevoice,hotkey]"

# （可选）全部功能
pip install -e ".[all]"
```

### 2. 下载模型（~450MB）

```bash
mvplugin download-model
```

> 📦 来源：[ModelScope](https://modelscope.cn/models/iic/SenseVoiceSmall)（国内快）· [HuggingFace](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)

### 3. 开始使用

```bash
mvplugin run          # 按 F2 开始/停止录音
mvplugin devices      # 查看麦克风列表
```

插上麦克风，按 F2，开口说话就行了。

---

## 📋 命令行

```bash
mvplugin run                          # 启动语音识别
mvplugin run --engine whisper         # 换用 Whisper
mvplugin devices                      # 列出音频设备
mvplugin download-model               # 下载模型

mvplugin dict list                    # 查看词典
mvplugin dict add "欧克二" "OKR"       # 添加替换规则

mvplugin test recording.wav           # 用文件测试
```

---

## ⚙️ 配置

编辑 `configs/config.yaml`：

```yaml
asr:
  engine: sensevoice          # sensevoice / doubao / whisper
  device: auto                # auto / cpu / cuda / mps

processors:
  pipeline:
    - filler_filter           # 去掉"嗯""那个""就是说"
    - dictionary_replace      # 自定义术语替换
    - llm_polish              # LLM 润色（可选）

  llm_enabled: false
  llm_api_key: ""
  llm_base_url: "https://api.openai.com/v1"
  llm_model: "gpt-4o-mini"

hotkey:
  key: f2
  mode: toggle                # toggle / push_to_talk
```

### 国产 LLM 配置示例

```yaml
# 通义千问
llm_base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
llm_model: "qwen-turbo"

# Kimi
llm_base_url: "https://api.moonshot.cn/v1"
llm_model: "moonshot-v1-8k"
```

### 环境变量

```bash
export MVPLUGIN_ASR_ENGINE=whisper
export MVPLUGIN_ASR_DEVICE=mps
export MVPLUGIN_LLM_API_KEY=sk-xxx
```

---

## 📖 自定义词典

编辑 `dictionaries/default.yaml`，**改了立刻生效**，不用重启：

```yaml
replacements:
  - from: "欧克二"
    to: "OKR"
  - from: ["赛恩斯沃伊斯", "森斯沃伊斯"]
    to: "SenseVoice"
  - from: "re:皮{1,2}迪"     # 支持正则
    to: "PPT"
```

---

## 🔌 引擎对比

| 引擎 | 本地 | 流式 | 速度 | 中文 | 多语言 | 大小 |
|------|------|------|------|------|--------|------|
| **SenseVoice-Small** ⭐ | ✅ | 分段 | ⚡⚡⚡ | ⭐⭐⭐⭐ | 50+ | ~450MB |
| **豆包 2.0** | ❌ 云端 | ✅ 真流式 | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | 中英 | — |
| **Whisper** | ✅ | 分段 | ⚡ | ⭐⭐⭐ | 99 | 75MB–3GB |

---

## 🆚 对比

| | **本项目** | Wispr Flow | 蛐蛐 QuQu | 闪电说 |
|---|---|---|---|---|
| **价格** | ✅ 免费开源 | $12/月 | 免费 | 付费 |
| **隐私** | ✅ 本地 | 云端 | 本地 | 云端 |
| **模型** | SenseVoice-Small | Whisper | Paraformer | 豆包 |
| **换引擎** | ✅ 改一行 | ❌ | ❌ | ❌ |
| **界面** | CLI + Python库 | GUI | GUI | GUI |
| **词典** | ✅ 热加载 | ❌ | ❌ | ✅ |
| **LLM 润色** | ✅ 任意API | ❌ | ✅ | 探索中 |

---

## 🗺️ 路线图

- [x] 核心 Pipeline：音频 → ASR → 后处理 → 输出
- [x] SenseVoice-Small / 豆包 / Whisper 引擎
- [x] 口语过滤 + 词典替换 + LLM 润色
- [x] 全局快捷键 + CLI 工具
- [ ] 剪贴板粘贴 / 模拟键盘输入
- [ ] 系统托盘状态指示
- [ ] WebSocket API
- [ ] GUI 界面
- [ ] PyPI 发包

---

## 🙏 致谢

- **[FunAudioLLM/SenseVoice](https://github.com/FunAudioLLM/SenseVoice)** — 核心 ASR 模型
- **[FunASR](https://github.com/modelscope/FunASR)** — 阿里开源语音识别工具包
- **[蛐蛐 QuQu](https://github.com/yan5xu/ququ)** — 桌面语音工作流灵感来源

---

## 🤝 参与贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)，欢迎 PR！

## 📄 许可证

[Apache License 2.0](LICENSE)

---

<div align="center">

**觉得有用？给个 ⭐ 吧**

Made by [Jon](https://github.com/Alexin09)

</div>
