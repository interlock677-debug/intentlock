from app.application.interfaces.nonce_store import NonceStore
from app.infrastructure.redis.client import RedisClient, RedisUnavailableError


class RedisNonceStore(NonceStore):
    """L2 distributed nonce store backed by Redis.

    Uses atomic SET NX EX to ensure concurrent requests cannot consume
    the same nonce successfully. Fails closed when Redis is unavailable
    to prevent replay attacks from bypassing the security control.
    """

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    def consume(self, nonce: str, ttl_seconds: int) -> bool:
        try:
            return self._redis.set_nx(f"nonce:{nonce}", "1", ex=ttl_seconds)
        except RedisUnavailableError:
            # Fail closed: if we cannot verify the nonce, reject it.
            return False

    def is_consumed(self, nonce: str) -> bool:
        return self._redis.get(f"nonce:{nonce}") is not None
