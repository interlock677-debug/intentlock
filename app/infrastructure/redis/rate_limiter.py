"""Distributed rate limiting backed by Redis.

Uses a fixed-window counter with atomic INCR + EXPIRE.  The window is
derived from the current time so that all application instances agree on
the same window boundaries, preventing bypass through process boundaries.

Security behavior:
    - Counting is atomic (single INCR) so concurrent requests are safe.
    - If Redis is unavailable, ``check()`` raises ``RedisUnavailableError``
      so callers can fail closed rather than silently becoming unlimited.
"""

from __future__ import annotations

import time

from app.infrastructure.redis.client import RedisClient

_KEY_PREFIX = "rate_limit"


class RedisRateLimiter:
    """Fixed-window distributed rate limiter using Redis counters."""

    def __init__(self, redis_client: RedisClient, window_seconds: int = 60) -> None:
        self._redis = redis_client
        self._window_seconds = window_seconds

    def check(self, route: str, client_key: str, limit: int) -> tuple[bool, int | None]:
        """Record a request and return ``(allowed, retry_after_seconds)``.

        ``allowed`` is ``False`` when the request exceeds *limit* within the
        current window.  ``retry_after_seconds`` is the number of seconds
        remaining in the window (used for the ``Retry-After`` header).

        Raises ``RedisUnavailableError`` if Redis cannot be reached, so the
        caller can fail closed.
        """
        window_id = int(time.time() // self._window_seconds)
        key = f"{_KEY_PREFIX}:{route}:{client_key}:{window_id}"
        count = self._redis.incr_or_raise(key, ex=self._window_seconds)
        if count > limit:
            retry_after = self._window_seconds - (int(time.time()) % self._window_seconds)
            return False, retry_after
        return True, None
