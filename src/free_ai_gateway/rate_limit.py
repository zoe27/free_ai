"""按 provider 的请求队列限流：同一 provider 的调用串行排队，按 rpm 间隔放行。"""

import asyncio
import logging
import time

logger = logging.getLogger("free_ai_gateway.rate_limit")


class ProviderRateLimiter:
    """FIFO 排队 + 最小间隔。asyncio.Lock 天然把并发 acquire 排成队列。"""

    def __init__(self, name: str, rpm: float | None):
        self.name = name
        self.rpm = rpm
        self._interval = (60.0 / rpm) if rpm and rpm > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next_ok = 0.0
        self._waiting = 0

    @property
    def waiting(self) -> int:
        return self._waiting

    @property
    def interval_s(self) -> float | None:
        return self._interval if self._interval > 0 else None

    async def acquire(self) -> None:
        if self._interval <= 0:
            return

        self._waiting += 1
        try:
            async with self._lock:
                now = time.monotonic()
                wait = self._next_ok - now
                if wait > 0:
                    logger.info(
                        "provider %s rate-limit queue: wait %.2fs (rpm=%.1f, waiting=%d)",
                        self.name,
                        wait,
                        self.rpm,
                        self._waiting,
                    )
                    await asyncio.sleep(wait)
                self._next_ok = time.monotonic() + self._interval
        finally:
            self._waiting -= 1
