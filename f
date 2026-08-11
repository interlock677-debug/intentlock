import contextlib
import logging

import redis

logger = logging.getLogger("intentlock.redis")


class RedisClient:
    """Redis connection manager with graceful degradation.

    Provides a consistent interface for Redis operations with explicit
    failure handling. Security-sensitive operations must fail closed
    when Redis is unavailable; non-security operations may fail open.
    """

    def __init__(self, url: str | None = None, *, enabled: bool = True) -> None:
        self._enabled = enabled and bool(url)
        self._client: redis.Redis | None = None
        if self._enabled and url:
            try:
                self._client = redis.Redis.from_url(url, decode_responses=True)
                self._client.ping()
            except redis.RedisError as exc:
                logger.warning("Redis unavailable at startup: %s", exc)
                self._client = None
                self._enabled = False

    @property
    def available(self) -> bool:
        return self._enabled and self._client is not None

    def set_nx(self, key: str, value: str, ex: int) -> bool:
        """Atomically set a key only if it does not exist.

        Returns True if the key was set, False if it already existed.
        Raises RedisUnavailableError if Redis is not available.
        """
        if not self.available or self._client is None:
            raise RedisUnavailableError("Redis is not available")
        try:
            return bool(self._client.set(key, value, ex=ex, nx=True))
        except redis.RedisError as exc:
            raise RedisUnavailableError(f"Redis operation failed: {exc}") from exc

    def get(self, key: str) -> str | None:
        """Get a value from Redis. Returns None if not found or unavailable."""
        if not self.available or self._client is None:
            return None
        try:
            result = self._client.get(key)
            if result is None:
                return None
            return str(result)
        except redis.RedisError as exc:
            logger.warning("Redis GET failed for key %s: %s", key, exc)
            return None

    def incr(self, key: str, ex: int | None = None) -> int | None:
        """Increment a counter. Returns None if Redis is unavailable."""
        if not self.available or self._client is None:
            return None
        try:
            value = self._client.incr(key)
            if ex is not None:
                self._client.expire(key, ex)
            return int(value)
        except redis.RedisError as exc:
            logger.warning("Redis INCR failed for key %s: %s", key, exc)
            return None

    def expire(self, key: str, seconds: int) -> bool:
        """Set a TTL on a key. Returns False if Redis is unavailable."""
        if not self.available or self._client is None:
            return False
        try:
            return bool(self._client.expire(key, seconds))
        except redis.RedisError as exc:
            logger.warning("Redis EXPIRE failed for key %s: %s", key, exc)
            return False

    def delete(self, key: str) -> bool:
        """Delete a key. Returns False if Redis is unavailable."""
        if not self.available or self._client is None:
            return False
        try:
            return bool(self._client.delete(key))
        except redis.RedisError as exc:
            logger.warning("Redis DELETE failed for key %s: %s", key, exc)
            return False

    def close(self) -> None:
        if self._client is not None:
            with contextlib.suppress(redis.RedisError):
                self._client.close()
            self._client = None


class RedisUnavailableError(Exception):
    """Raised when a Redis operation is required but Redis is unavailable."""
