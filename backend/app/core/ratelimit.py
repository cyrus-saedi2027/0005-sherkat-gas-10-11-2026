"""Sliding-window rate limiting (R36): OTP, logins, uploads, general API.

Memory backend for dev/tests/single-process; Redis backend for multi-worker
production (set GAZYAR_RATELIMIT_BACKEND=redis). Limits are expressed in the
call sites with numbers read from settings, never hard-coded there.
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import AppError


class _Backend(Protocol):
    def hit(self, key: str, limit: int, window_s: int) -> tuple[bool, int]: ...
    def reset(self) -> None: ...


class MemoryBackend:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window_s:
                q.popleft()
            if len(q) >= limit:
                return False, max(1, math.ceil(q[0] + window_s - now))
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class RedisBackend:
    def __init__(self, url: str) -> None:
        import redis

        self._r = redis.Redis.from_url(url)

    def hit(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        now = time.time()
        k = f"rl:{key}"
        pipe = self._r.pipeline()
        pipe.zremrangebyscore(k, 0, now - window_s)
        pipe.zcard(k)
        pipe.zrange(k, 0, 0, withscores=True)
        _, count, oldest = pipe.execute()
        if count >= limit:
            first = oldest[0][1] if oldest else now
            return False, max(1, math.ceil(first + window_s - now))
        pipe = self._r.pipeline()
        pipe.zadd(k, {f"{now}:{time.perf_counter_ns()}": now})
        pipe.expire(k, window_s + 1)
        pipe.execute()
        return True, 0

    def reset(self) -> None:  # tests only
        for k in self._r.scan_iter("rl:*"):
            self._r.delete(k)


_backend: _Backend | None = None


def backend() -> _Backend:
    global _backend
    if _backend is None:
        s = get_settings()
        _backend = RedisBackend(s.redis_url) if s.ratelimit_backend == "redis" else MemoryBackend()
    return _backend


def enforce(key: str, limit: int, window_s: int, message: str | None = None) -> None:
    """Count a hit; raise 429 `rate_limited` with Retry-After when over the limit."""
    ok, retry = backend().hit(key, limit, window_s)
    if not ok:
        raise AppError(
            "rate_limited",
            message or "تعداد درخواست‌ها بیش از حد مجاز است؛ کمی بعد دوباره تلاش کنید.",
            429,
            {"retry_after": retry},
        )


def reset() -> None:
    backend().reset()
