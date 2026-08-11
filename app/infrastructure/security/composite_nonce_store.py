from app.application.interfaces.nonce_store import NonceStore


class CompositeNonceStore(NonceStore):
    """L1 + L2 nonce store combining local memory and distributed Redis.

    The L1 memory store provides fast local replay protection. The L2
    Redis store provides distributed replay protection across instances.

    Security decision: If Redis is unavailable, the L2 store fails closed
    (rejects the nonce) to prevent replay attacks from bypassing the
    security control. The L1 store still provides local protection.
    """

    def __init__(self, l1: NonceStore, l2: NonceStore | None = None) -> None:
        self._l1 = l1
        self._l2 = l2

    def consume(self, nonce: str, ttl_seconds: int) -> bool:
        # Check L1 first for fast local rejection of known nonces.
        if self._l1.is_consumed(nonce):
            return False

        # Check L2 for distributed replay protection.
        if self._l2 is not None and not self._l2.consume(nonce, ttl_seconds):
            return False

        # Record in L1 for fast local rejection.
        self._l1.consume(nonce, ttl_seconds)
        return True

    def is_consumed(self, nonce: str) -> bool:
        return self._l1.is_consumed(nonce) or (
            self._l2 is not None and self._l2.is_consumed(nonce)
        )
