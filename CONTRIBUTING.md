# Contributing to mutimodel-voice-plugin

Thanks for your interest! Here's how to get involved.

## Development Setup

```bash
git clone https://github.com/Alexin09/mutimodel-voice-plugin.git
cd mutimodel-voice-plugin
pip install -e ".[dev,all]"
```

## Run Tests

```bash
pytest
```

## Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting:

```bash
ruff check src/
ruff format src/
```

## How to Contribute

### Report Bugs
Open an [Issue](https://github.com/Alexin09/mutimodel-voice-plugin/issues) with:
- Steps to reproduce
- Expected vs actual behavior
- OS / Python version

### Suggest Features
Open an Issue with the `enhancement` label. Describe:
- The problem you're solving
- Your proposed solution

### Submit Code

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit: `git commit -m "feat: add my feature"`
6. Push: `git push origin feature/my-feature`
7. Open a Pull Request

### Add a New ASR Engine

The engine system is designed to be extensible. See `src/mutimodel_voice_plugin/engines/base.py` for the interface. A new engine needs:

1. Implement `BaseASREngine` (~50 lines)
2. Register with `EngineRegistry.register("your_engine", YourEngine)`
3. Add a test in `tests/`

### Add a New Processor

Post-processing is a pipeline. See `src/mutimodel_voice_plugin/processors/base.py`. A new processor needs:

1. Implement `BaseProcessor.process()`
2. Add to the pipeline in `config.yaml`

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new ASR engine for XYZ
fix: handle empty audio chunks gracefully
docs: update README with new config options
refactor: simplify pipeline execution logic
test: add unit tests for dictionary replacement
```

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
