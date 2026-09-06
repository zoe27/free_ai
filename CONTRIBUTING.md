# Contributing

Thanks for your interest in **free-ai-gateway**.

## How to contribute

1. Fork the repo (or create a branch if you have write access).
2. Create a feature branch from `master` — do not push directly to `master`.
3. Make your change (keep diffs focused; match existing style).
4. Open a Pull Request with a short summary of *why* the change is needed.

## Local setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
cp env.example .env   # fill at least one provider key
.venv/bin/uvicorn free_ai_gateway.main:app --host 0.0.0.0 --port 8000
```

## Ideas that help

- New OpenAI-compatible free providers via `providers.yaml` (prefer config over code)
- Bug fixes, clearer docs, tests
- Streaming (`stream=true`) and deployment notes

## Security

Do **not** commit API keys or `.env`. Report security issues privately to the maintainer if possible.
