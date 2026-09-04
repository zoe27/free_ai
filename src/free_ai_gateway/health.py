"""Provider 健康状态：失败即短暂 cooldown，指数递增，进程内内存态，重启即重置。"""

import time

_INITIAL_COOLDOWN = 60.0
_MAX_COOLDOWN = 1800.0

_state: dict[str, dict[str, float]] = {}


def is_available(provider_name: str) -> bool:
    entry = _state.get(provider_name)
    return entry is None or time.monotonic() >= entry["cooldown_until"]


def record_failure(provider_name: str) -> None:
    entry = _state.setdefault(provider_name, {"fail_count": 0.0, "cooldown_until": 0.0})
    entry["fail_count"] += 1
    cooldown = min(_INITIAL_COOLDOWN * (2 ** (entry["fail_count"] - 1)), _MAX_COOLDOWN)
    entry["cooldown_until"] = time.monotonic() + cooldown


def record_success(provider_name: str) -> None:
    _state.pop(provider_name, None)
