from unittest.mock import MagicMock, patch

import pytest
import redis

from app.infrastructure.redis.client import RedisClient, RedisUnavailableError
from app.infrastructure.redis.nonce_store import RedisNonceStore
from app.infrastructure.security.composite_nonce_store import CompositeNonceStore
from app.infrastructure.security.memory_nonce_store import MemoryNonceStore


def test_redis_client_init_disabled() -> None:
    client = RedisClient(None, enabled=False)
    assert not client.available
    client.close()


def test_redis_client_init_connection_failure() -> None:
    with patch("redis.Redis.from_url", side_effect=redis.RedisError("Conn failed")):
        client = RedisClient("redis://localhost:6379/0", enabled=True)
        assert not client.available


def test_redis_client_set_nx_branches() -> None:
    client = RedisClient(None, enabled=False)
    with pytest.raises(RedisUnavailableError):
        client.set_nx("key", "val", ex=10)

    # Mock available client
    mock_redis = MagicMock()
    client._client = mock_redis
    client._enabled = True

    mock_redis.set.return_value = True
    assert client.set_nx("key", "val", ex=10) is True

    mock_redis.set.return_value = None
    assert client.set_nx("key", "val", ex=10) is False

    mock_redis.set.side_effect = redis.RedisError("Fail")
    with pytest.raises(RedisUnavailableError):
        client.set_nx("key", "val", ex=10)


def test_redis_client_get_branches() -> None:
    client = RedisClient(None, enabled=False)
    assert client.get("key") is None

    mock_redis = MagicMock()
    client._client = mock_redis
    client._enabled = True

    mock_redis.get.return_value = "hello"
    assert client.get("key") == "hello"

    mock_redis.get.return_value = None
    assert client.get("key") is None

    mock_redis.get.side_effect = redis.RedisError("Err")
    assert client.get("key") is None


def test_redis_client_incr_branches() -> None:
    client = RedisClient(None, enabled=False)
    assert client.incr("key") is None

    mock_redis = MagicMock()
    client._client = mock_redis
    client._enabled = True

    mock_redis.incr.return_value = 5
    assert client.incr("key", ex=60) == 5
    mock_redis.expire.assert_called_with("key", 60)

    mock_redis.incr.side_effect = redis.RedisError("Err")
    assert client.incr("key") is None


def test_redis_client_incr_or_raise_branches() -> None:
    # Unavailable -> raises
    client = RedisClient(None, enabled=False)
    with pytest.raises(RedisUnavailableError):
        client.incr_or_raise("key")

    # Available -> returns incremented value
    mock_redis = MagicMock()
    client._client = mock_redis
    client._enabled = True

    mock_redis.incr.return_value = 5
    assert client.incr_or_raise("key", ex=60) == 5
    mock_redis.expire.assert_called_with("key", 60)

    # Without ex -> no expire call
    mock_redis.reset_mock()
    mock_redis.incr.return_value = 7
    assert client.incr_or_raise("key") == 7
    mock_redis.expire.assert_not_called()

    # Redis error -> raises
    mock_redis.incr.side_effect = redis.RedisError("Err")
    with pytest.raises(RedisUnavailableError):
        client.incr_or_raise("key")


def test_redis_client_expire_and_delete_branches() -> None:
    client = RedisClient(None, enabled=False)
    assert client.expire("key", 10) is False
    assert client.delete("key") is False

    mock_redis = MagicMock()
    client._client = mock_redis
    client._enabled = True

    mock_redis.expire.return_value = True
    assert client.expire("key", 10) is True

    mock_redis.expire.side_effect = redis.RedisError("Err")
    assert client.expire("key", 10) is False

    mock_redis.delete.return_value = True
    assert client.delete("key") is True

    mock_redis.delete.side_effect = redis.RedisError("Err")
    assert client.delete("key") is False


def test_redis_client_close() -> None:
    mock_redis = MagicMock()
    client = RedisClient(None, enabled=False)
    client._client = mock_redis
    client.close()
    mock_redis.close.assert_called_once()
    assert client._client is None


def test_redis_nonce_store() -> None:
    mock_client = MagicMock()
    store = RedisNonceStore(mock_client)

    mock_client.set_nx.return_value = True
    assert store.consume("nonce1", 60) is True

    mock_client.set_nx.side_effect = RedisUnavailableError("Down")
    assert store.consume("nonce2", 60) is False

    mock_client.get.return_value = "1"
    assert store.is_consumed("nonce1") is True

    mock_client.get.return_value = None
    assert store.is_consumed("nonce3") is False


def test_redis_client_init_success() -> None:
    with patch("redis.Redis.from_url") as mock_from_url:
        mock_instance = MagicMock()
        mock_from_url.return_value = mock_instance
        client = RedisClient("redis://localhost:6379/0", enabled=True)
        assert client.available is True
        mock_instance.ping.assert_called_once()


def test_composite_nonce_store() -> None:
    l1 = MemoryNonceStore()
    mock_l2 = MagicMock()

    composite = CompositeNonceStore(l1=l1, l2=mock_l2)

    # L2 consume returns False (e.g. unavailable or already consumed)
    mock_l2.consume.return_value = False
    assert composite.consume("n1", 60) is False

    # L2 consume returns True -> recorded in L1 and L2
    mock_l2.consume.return_value = True
    assert composite.consume("n1", 60) is True

    # Subsequent consume of n1 hits L1 check and returns False
    assert composite.consume("n1", 60) is False

    # is_consumed checks L1 then L2
    assert composite.is_consumed("n1") is True

    mock_l2.is_consumed.return_value = True
    assert composite.is_consumed("n2") is True

    mock_l2.is_consumed.return_value = False
    assert composite.is_consumed("n3") is False

    # Composite with L2=None
    comp_no_l2 = CompositeNonceStore(l1=l1, l2=None)
    assert comp_no_l2.consume("n4", 60) is True
    assert comp_no_l2.is_consumed("n4") is True
