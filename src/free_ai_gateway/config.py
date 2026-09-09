"""加载 .env + providers.yaml，产出启用的 provider 配置和别名链。"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_ENV_VAR_RE = re.compile(r"\$\{(\w+)\}")


def _resolve_env(value: str) -> str:
    return _ENV_VAR_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str | None
    rpm: float | None = None  # 每分钟请求上限；None / <=0 表示不限流


@dataclass(frozen=True)
class AliasStep:
    provider: str
    model: str


@dataclass
class GatewayConfig:
    providers: dict[str, ProviderConfig]
    aliases: dict[str, list[AliasStep]]
    gateway_token: str | None


def load_config(path: str | Path = "providers.yaml") -> GatewayConfig:
    raw = yaml.safe_load(Path(path).read_text())

    providers: dict[str, ProviderConfig] = {}
    for name, spec in raw.get("providers", {}).items():
        api_key_env = spec.get("api_key_env")
        api_key = os.environ.get(api_key_env) if api_key_env else None
        if api_key_env and not api_key:
            continue  # 没配 key，跳过，不进候选链
        base_url = _resolve_env(spec["base_url"]).rstrip("/")
        # 如 OLLAMA_BASE_URL 留空时，${OLLAMA_BASE_URL}/v1 会变成 "/v1"，视为未启用
        if not base_url or base_url == "/v1":
            continue
        rpm = spec.get("rpm")
        providers[name] = ProviderConfig(
            name=name,
            base_url=base_url,
            api_key=api_key,
            rpm=float(rpm) if rpm is not None else None,
        )

    aliases: dict[str, list[AliasStep]] = {}
    for alias, chain in raw.get("aliases", {}).items():
        steps = [
            AliasStep(provider=step["provider"], model=step["model"])
            for step in chain
            if step["provider"] in providers
        ]
        if steps:
            aliases[alias] = steps

    return GatewayConfig(
        providers=providers,
        aliases=aliases,
        gateway_token=os.environ.get("GATEWAY_TOKEN"),
    )
