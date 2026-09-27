"""A small, dependency-free sliding-window rate limiter.

Storage is in-process. That is correct for a single worker and for local
development; a multi-process deployment should back ``InMemoryRateLimiter`` with
Redis (same ``check`` contract) — see ``RateLimiter`` protocol below.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Protocol


class RateLimiter(Protocol):
    def check(self, key: str, limit: int, window_seconds: int) -> int | None:
        """Register a hit.

        Returns ``None`` when the request is allowed, or the number of seconds
        to wait before retrying when the limit is exceeded.
        """


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> int | None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(bucket[0] + window_seconds - now) + 1)
                return retry_after
            bucket.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def parse_limit(spec: str) -> tuple[int, int]:
    """Parse ``"10/minute"`` into ``(10, 60)``."""
    try:
        count_str, period = spec.split("/", 1)
        count = int(count_str)
    except ValueError as exc:  # pragma: no cover - guarded by config defaults
        raise ValueError(f"Invalid rate limit spec: {spec!r}") from exc

    unit = period.strip().lower().rstrip("s")
    windows = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    if unit not in windows:
        raise ValueError(f"Invalid rate limit period: {period!r}")
    return count, windows[unit]


# Process-wide limiter instance.
rate_limiter: RateLimiter = InMemoryRateLimiter()
