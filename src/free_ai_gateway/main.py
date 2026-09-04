import asyncio
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from free_ai_gateway.config import load_config
from free_ai_gateway.providers.registry import build_providers
from free_ai_gateway.router import NoProviderAvailable, Router
from free_ai_gateway.schemas import ChatCompletionRequest, ProviderError

logging.basicConfig(level=logging.INFO)

_config = load_config()
_providers = build_providers(_config)
_router = Router(_config, _providers)
_STATIC_DIR = Path(__file__).parent / "static"

# 每个 provider 用哪个 model 测试：取它在 aliases 里第一次出现时配的那个 model
_test_model: dict[str, str] = {}
for _chain in _config.aliases.values():
    for _step in _chain:
        _test_model.setdefault(_step.provider, _step.model)

app = FastAPI(title="free-ai-gateway")


@app.get("/", include_in_schema=False)
async def ui() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


def _check_token(request: Request) -> None:
    if not _config.gateway_token:
        return
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if token != _config.gateway_token:
        raise HTTPException(status_code=401, detail="invalid token")


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    _check_token(request)
    if body.stream:
        raise HTTPException(status_code=400, detail="流式响应暂未支持")
    try:
        return await _router.chat_completion(body.model_dump(exclude_none=True))
    except NoProviderAvailable as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.get("/v1/models")
async def list_models(request: Request):
    _check_token(request)
    aliases = [{"id": alias, "object": "model", "kind": "alias"} for alias in _config.aliases]
    providers = [
        {"id": f"{name}/{model}", "object": "model", "kind": "provider"}
        for name, model in _test_model.items()
    ]
    return {"object": "list", "data": aliases + providers}


@app.get("/v1/providers/health")
async def providers_health(request: Request):
    _check_token(request)

    async def check_one(name: str):
        provider = _providers[name]
        model = _test_model.get(name)
        if model is None:
            return {"provider": name, "ok": False, "error": "没有可测试的 model（未出现在任何 alias 里）"}

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }
        start = time.monotonic()
        try:
            await provider.chat_completion(payload)
        except ProviderError as e:
            return {
                "provider": name,
                "model": model,
                "ok": False,
                "latency_ms": round((time.monotonic() - start) * 1000),
                "error": str(e),
            }
        return {
            "provider": name,
            "model": model,
            "ok": True,
            "latency_ms": round((time.monotonic() - start) * 1000),
        }

    results = await asyncio.gather(*(check_one(name) for name in _providers))
    queue = {}
    for name, provider in _providers.items():
        limiter = getattr(provider, "limiter", None)
        if limiter is not None:
            queue[name] = {
                "rpm": limiter.rpm,
                "waiting": limiter.waiting,
                "interval_s": round(limiter.interval_s, 3) if limiter.interval_s else None,
            }
    return {"results": results, "rate_limit": queue}


def run() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("GATEWAY_HOST", "0.0.0.0"),
        port=int(os.environ.get("GATEWAY_PORT", "8000")),
    )


if __name__ == "__main__":
    run()
