# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-04-08

### Added
- Core pipeline: Audio Capture → ASR Engine → Post-Processing → Output
- **SenseVoice-Small** as default ASR engine (local, ~450MB, 50+ languages)
- **Doubao Streaming ASR 2.0** engine (cloud, real-time streaming)
- **Whisper** engine (local, via faster-whisper)
- Pluggable engine architecture with `EngineRegistry`
- Post-processing pipeline:
  - Filler word filter (Chinese + English, 30+ patterns)
  - Custom dictionary replacement (YAML, hot-reload, regex support)
  - LLM polish (any OpenAI-compatible API)
- Audio device auto-detection (DJI Mic priority)
- Global hotkey (F2, Toggle / Push-to-Talk modes)
- CLI tool: `mvplugin run|devices|dict|download-model|test`
- Configuration system: YAML + environment variable overrides
- Default dictionary with common ASR misrecognition fixes
- Unit tests for pipeline and engine registry
