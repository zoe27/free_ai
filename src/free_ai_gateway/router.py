"""别名解析 + provider 优先级 fallback。"""

import logging
from typing import Any

from free_ai_gateway import health
from free_ai_gateway.config import GatewayConfig
from free_ai_gateway.providers.base import Provider
from free_ai_gateway.schemas import ProviderError

logger = logging.getLogger("free_ai_gateway.router")


class NoProviderAvailable(Exception):
    pass


class Router:
    def __init__(self, config: GatewayConfig, providers: dict[str, Provider]):
        self._config = config
        self._providers = providers

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = payload["model"]

        if "/" in model:
            provider_name, real_model = model.split("/", 1)
            chain = [(provider_name, real_model)]
        else:
            alias = self._config.aliases.get(model)
            if not alias:
                raise NoProviderAvailable(f"未知的 model/别名: {model}")
            chain = [(step.provider, step.model) for step in alias]

        last_error: Exception | None = None
        attempts = 0
        for provider_name, real_model in chain:
            provider = self._providers.get(provider_name)
            if provider is None or not health.is_available(provider_name):
                continue

            attempts += 1
            provider_payload = {**payload, "model": real_model}
            try:
                result = await provider.chat_completion(provider_payload)
            except ProviderError as e:
                logger.warning("provider %s 失败: %s", provider_name, e)
                if e.retryable:
                    health.record_failure(provider_name)
                last_error = e
                continue

            health.record_success(provider_name)
            result["_gateway"] = {
                "alias": model,
                "provider": provider_name,
                "model": real_model,
                "fallback": attempts > 1,
            }
            return result

        raise NoProviderAvailable(
            f"model '{model}' 的所有候选 provider 都不可用: {last_error}"
        )
