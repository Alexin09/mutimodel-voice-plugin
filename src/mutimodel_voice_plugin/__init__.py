"""
mutimodel-voice-plugin: 多模型语音识别 + 智能后处理 Pipeline

Architecture:
    [硬件层] DJI Mic 无线麦克风 → 高质量音频信号
        ↓
    [音频捕获层] 自动设备发现 + 实时音频流捕获
        ↓
    [ASR 引擎层] 可插拔后端（SenseVoice-Small / 豆包 / Whisper）
        ↓
    [后处理层] Pipeline: 口语过滤 → 词典替换 → LLM 润色 → 结构化输出

Core ASR Model: FunAudioLLM/SenseVoice-Small
    - ModelScope: https://modelscope.cn/models/iic/SenseVoiceSmall
    - HuggingFace: https://huggingface.co/FunAudioLLM/SenseVoiceSmall
"""

__version__ = "0.1.0"
