"""按 GatewayConfig 实例化所有启用的 provider，并套上按 rpm 排队的限流。"""

from typing import Any

from free_ai_gateway.config import GatewayConfig
from free_ai_gateway.providers.base import Provider
from free_ai_gateway.providers.openai_compatible import OpenAICompatibleProvider
from free_ai_gateway.rate_limit import ProviderRateLimiter


class RateLimitedProvider:
    def __init__(self, inner: Provider, limiter: ProviderRateLimiter):
        self.name = inner.name
        self._inner = inner
        self.limiter = limiter

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self.limiter.acquire()
        return await self._inner.chat_completion(payload)


def build_providers(config: GatewayConfig) -> dict[str, Provider]:
    providers: dict[str, Provider] = {}
    for name, cfg in config.providers.items():
        inner = OpenAICompatibleProvider(name=name, base_url=cfg.base_url, api_key=cfg.api_key)
        limiter = ProviderRateLimiter(name=name, rpm=cfg.rpm)
        providers[name] = RateLimitedProvider(inner, limiter)
    return providers
