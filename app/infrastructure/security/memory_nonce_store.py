import threading
import time
from collections import OrderedDict

from app.application.interfaces.nonce_store import NonceStore


class MemoryNonceStore(NonceStore):
    """L1 in-process bounded nonce store.

    Thread-safe bounded LRU cache with TTL and size limits. This provides
    fast local replay protection but is NOT sufficient for distributed
    deployments — use RedisNonceStore as the L2 layer.
    """

    def __init__(self, *, max_entries: int = 100_000, ttl_seconds: int = 300) -> None:
        self._max_entries = max_entries
        self._default_ttl = ttl_seconds
        self._entries: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def consume(self, nonce: str, ttl_seconds: int) -> bool:
        with self._lock:
            now = time.monotonic()
            self._evict_expired(now)

            if nonce in self._entries:
                return False

            self._entries[nonce] = now + ttl_seconds
            self._evict_overflow()
            return True

    def is_consumed(self, nonce: str) -> bool:
        with self._lock:
            now = time.monotonic()
            self._evict_expired(now)
            return nonce in self._entries

    def _evict_expired(self, now: float) -> None:
        expired = [key for key, expires_at in self._entries.items() if expires_at <= now]
        for key in expired:
            self._entries.pop(key, None)

    def _evict_overflow(self) -> None:
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
