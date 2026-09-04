"""Provider 抽象接口。所有来源（OpenAI 兼容或自定义）都实现这个接口。"""

from typing import Any, Protocol


class Provider(Protocol):
    name: str

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """payload 是 OpenAI ChatCompletion 请求体（已替换成该 provider 的真实 model 名）。
        返回值必须是 OpenAI ChatCompletion 响应格式的 dict。
        失败时抛 schemas.ProviderError。
        """
        ...
