import threading
from concurrent.futures import ThreadPoolExecutor

from app.infrastructure.security.composite_nonce_store import CompositeNonceStore
from app.infrastructure.security.memory_nonce_store import MemoryNonceStore


class TestMemoryNonceStore:
    def test_consume_returns_true_first_time(self) -> None:
        store = MemoryNonceStore()
        assert store.consume("nonce-1", ttl_seconds=60) is True

    def test_consume_returns_false_on_replay(self) -> None:
        store = MemoryNonceStore()
        assert store.consume("nonce-1", ttl_seconds=60) is True
        assert store.consume("nonce-1", ttl_seconds=60) is False

    def test_is_consumed(self) -> None:
        store = MemoryNonceStore()
        assert store.is_consumed("nonce-1") is False
        store.consume("nonce-1", ttl_seconds=60)
        assert store.is_consumed("nonce-1") is True

    def test_ttl_expiry(self) -> None:
        store = MemoryNonceStore(ttl_seconds=1)
        assert store.consume("nonce-1", ttl_seconds=1) is True
        # Simulate expiry by using a negative TTL
        store._entries["nonce-1"] = 0.0  # type: ignore[attr-defined]
        assert store.is_consumed("nonce-1") is False

    def test_max_entries_eviction(self) -> None:
        store = MemoryNonceStore(max_entries=2)
        assert store.consume("nonce-1", ttl_seconds=60) is True
        assert store.consume("nonce-2", ttl_seconds=60) is True
        assert store.consume("nonce-3", ttl_seconds=60) is True
        # nonce-1 should have been evicted
        assert store.is_consumed("nonce-1") is False
        assert store.is_consumed("nonce-2") is True
        assert store.is_consumed("nonce-3") is True

    def test_concurrent_consumption(self) -> None:
        """Concurrent requests must not consume the same nonce twice."""
        store = MemoryNonceStore()
        results: list[bool] = []
        lock = threading.Lock()

        def consume() -> None:
            result = store.consume("shared-nonce", ttl_seconds=60)
            with lock:
                results.append(result)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(consume) for _ in range(10)]
            for future in futures:
                future.result()

        assert results.count(True) == 1
        assert results.count(False) == 9


class TestCompositeNonceStore:
    def test_consume_without_l2(self) -> None:
        l1 = MemoryNonceStore()
        store = CompositeNonceStore(l1=l1)
        assert store.consume("nonce-1", ttl_seconds=60) is True
        assert store.consume("nonce-1", ttl_seconds=60) is False

    def test_consume_with_l2(self) -> None:
        l1 = MemoryNonceStore()
        l2 = MemoryNonceStore()
        store = CompositeNonceStore(l1=l1, l2=l2)
        assert store.consume("nonce-1", ttl_seconds=60) is True
        assert store.consume("nonce-1", ttl_seconds=60) is False

    def test_l2_rejects_replay(self) -> None:
        """If L2 rejects, the composite store must reject."""
        l1 = MemoryNonceStore()
        l2 = MemoryNonceStore()
        store = CompositeNonceStore(l1=l1, l2=l2)

        # First consumption succeeds
        assert store.consume("nonce-1", ttl_seconds=60) is True

        # Second consumption fails because L2 already has it
        assert store.consume("nonce-1", ttl_seconds=60) is False
