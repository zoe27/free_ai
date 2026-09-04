"""通用 adapter：适用于所有暴露 /chat/completions 且走 Bearer token 的来源
（Groq / OpenRouter / Gemini(openai 兼容端点) / Cerebras / Together / DeepSeek / Moonshot / Ollama ...）。"""

from typing import Any

import httpx

from free_ai_gateway.schemas import ProviderError

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class OpenAICompatibleProvider:
    def __init__(self, name: str, base_url: str, api_key: str | None, timeout: float = 30.0):
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.TimeoutException as e:
            raise ProviderError(f"{self.name} timeout: {e}", retryable=True) from e
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.name} connection error: {e}", retryable=True) from e

        if resp.status_code in RETRYABLE_STATUS:
            raise ProviderError(
                f"{self.name} returned {resp.status_code}: {resp.text[:200]}", retryable=True
            )
        if resp.status_code >= 400:
            raise ProviderError(
                f"{self.name} returned {resp.status_code}: {resp.text[:200]}", retryable=False
            )

        return resp.json()
