"""Comprehensive tests for distributed rate limiting.

Covers:
    - RedisRateLimiter (atomic counting, windows, isolation, failure modes)
    - RateLimitMiddleware with Redis (distributed, fail-closed, Retry-After)
    - In-memory fallback behavior
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure.redis.client import RedisClient, RedisUnavailableError
from app.infrastructure.redis.rate_limiter import RedisRateLimiter
from app.presentation.api.middleware.rate_limit import (
    RateLimitMiddleware,
    _get_client_ip,
    reset_rate_limits,
)

# --------------------------------------------------------------------------- #
# RedisRateLimiter — basic counting
# --------------------------------------------------------------------------- #


def _mock_redis_client() -> MagicMock:
    """Return a mock RedisClient that is available."""
    client = MagicMock(spec=RedisClient)
    client.available = True
    return client


def test_redis_rate_limiter_under_limit() -> None:
    client = _mock_redis_client()
    client.incr_or_raise.return_value = 1
    limiter = RedisRateLimiter(client, window_seconds=60)

    allowed, retry_after = limiter.check("/api/v1/auth/login", "client-1", limit=5)
    assert allowed is True
    assert retry_after is None


def test_redis_rate_limiter_exactly_at_limit() -> None:
    client = _mock_redis_client()
    client.incr_or_raise.return_value = 5
    limiter = RedisRateLimiter(client, window_seconds=60)

    allowed, retry_after = limiter.check("/api/v1/auth/login", "client-1", limit=5)
    assert allowed is True
    assert retry_after is None


def test_redis_rate_limiter_over_limit() -> None:
    client = _mock_redis_client()
    client.incr_or_raise.return_value = 6
    limiter = RedisRateLimiter(client, window_seconds=60)

    allowed, retry_after = limiter.check("/api/v1/auth/login", "client-1", limit=5)
    assert allowed is False
    assert retry_after is not None
    assert 0 < retry_after <= 60


def test_redis_rate_limiter_uses_windowed_key() -> None:
    client = _mock_redis_client()
    client.incr_or_raise.return_value = 1
    limiter = RedisRateLimiter(client, window_seconds=60)

    limiter.check("/api/v1/auth/login", "client-1", limit=5)
    # The key must include route, client, and window ID.
    key = client.incr_or_raise.call_args[0][0]
    assert key.startswith("rate_limit:/api/v1/auth/login:client-1:")
    # TTL must be set to the window.
    assert client.incr_or_raise.call_args[1]["ex"] == 60


def test_redis_rate_limiter_multiple_clients_isolated() -> None:
    client = _mock_redis_client()
    limiter = RedisRateLimiter(client, window_seconds=60)

    # Client A exceeds limit.
    client.incr_or_raise.return_value = 6
    allowed_a, _ = limiter.check("/api/v1/auth/login", "client-a", limit=5)
    assert allowed_a is False

    # Client B is under limit (different key).
    client.incr_or_raise.return_value = 1
    allowed_b, _ = limiter.check("/api/v1/auth/login", "client-b", limit=5)
    assert allowed_b is True


def test_redis_rate_limiter_multiple_endpoints_isolated() -> None:
    client = _mock_redis_client()
    limiter = RedisRateLimiter(client, window_seconds=60)

    # Login endpoint exceeds limit.
    client.incr_or_raise.return_value = 6
    allowed_login, _ = limiter.check("/api/v1/auth/login", "client-1", limit=5)
    assert allowed_login is False

    # Intent endpoint is under limit (different key).
    client.incr_or_raise.return_value = 1
    allowed_intent, _ = limiter.check("/api/v1/intent/verify", "client-1", limit=5)
    assert allowed_intent is True


def test_redis_rate_limiter_window_reset() -> None:
    client = _mock_redis_client()
    limiter = RedisRateLimiter(client, window_seconds=60)

    # Simulate a new window by patching time.
    with patch("app.infrastructure.redis.rate_limiter.time.time") as mock_time:
        mock_time.return_value = 100.0
        client.incr_or_raise.return_value = 6
        allowed, _ = limiter.check("/api/v1/auth/login", "client-1", limit=5)
        assert allowed is False

        # New window (time advances past 60s boundary).
        mock_time.return_value = 160.0
        client.incr_or_raise.return_value = 1
        allowed, _ = limiter.check("/api/v1/auth/login", "client-1", limit=5)
        assert allowed is True


def test_redis_rate_limiter_retry_after_calculated() -> None:
    client = _mock_redis_client()
    limiter = RedisRateLimiter(client, window_seconds=60)

    with patch("app.infrastructure.redis.rate_limiter.time.time") as mock_time:
        mock_time.return_value = 30.0  # 30s into the window
        client.incr_or_raise.return_value = 6
        allowed, retry_after = limiter.check("/api/v1/auth/login", "client-1", limit=5)
        assert allowed is False
        assert retry_after == 30  # 60 - 30


def test_redis_rate_limiter_redis_unavailable_raises() -> None:
    client = _mock_redis_client()
    client.incr_or_raise.side_effect = RedisUnavailableError("Redis down")
    limiter = RedisRateLimiter(client, window_seconds=60)

    with pytest.raises(RedisUnavailableError):
        limiter.check("/api/v1/auth/login", "client-1", limit=5)


def test_redis_rate_limiter_redis_timeout_raises() -> None:
    client = _mock_redis_client()
    client.incr_or_raise.side_effect = RedisUnavailableError("Redis timeout")
    limiter = RedisRateLimiter(client, window_seconds=60)

    with pytest.raises(RedisUnavailableError):
        limiter.check("/api/v1/auth/login", "client-1", limit=5)


def test_redis_rate_limiter_concurrent_requests_atomic() -> None:
    """Concurrent requests must be counted atomically via INCR."""
    client = _mock_redis_client()
    limiter = RedisRateLimiter(client, window_seconds=60)

    # Simulate 6 concurrent requests each incrementing the counter.
    counts = [1, 2, 3, 4, 5, 6]
    results = []
    for count in counts:
        client.incr_or_raise.return_value = count
        allowed, _ = limiter.check("/api/v1/auth/login", "client-1", limit=5)
        results.append(allowed)

    # First 5 allowed, 6th denied.
    assert results == [True, True, True, True, True, False]


# --------------------------------------------------------------------------- #
# RateLimitMiddleware — Redis-backed
# --------------------------------------------------------------------------- #


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/auth/login")
    async def login() -> dict[str, str]:
        return {"token": "ok"}

    @app.get("/api/v1/intent/verify")
    async def intent() -> dict[str, str]:
        return {"ok": "true"}

    return app


def test_middleware_uses_redis_when_available() -> None:
    app = _make_app()
    redis_client = _mock_redis_client()
    redis_client.available = True
    redis_client.incr_or_raise.return_value = 1

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 5
        resp = client.get("/api/v1/auth/login")
    assert resp.status_code == 200


def test_middleware_redis_returns_429_with_retry_after() -> None:
    app = _make_app()
    redis_client = _mock_redis_client()
    redis_client.available = True
    redis_client.incr_or_raise.return_value = 6

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 5
        resp = client.get("/api/v1/auth/login")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_middleware_redis_429_without_retry_after() -> None:
    """Cover the defensive branch where retry_after is None."""
    app = _make_app()
    redis_client = _mock_redis_client()
    redis_client.available = True

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    reset_rate_limits()

    client = TestClient(app)
    with (
        patch("app.presentation.api.middleware.rate_limit.RedisRateLimiter") as mock_limiter_cls,
        patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings,
    ):
        mock_limiter = MagicMock()
        mock_limiter.check.return_value = (False, None)
        mock_limiter_cls.return_value = mock_limiter
        mock_settings.return_value.rate_limit_login_per_minute = 5
        resp = client.get("/api/v1/auth/login")
    assert resp.status_code == 429
    assert "Retry-After" not in resp.headers


def test_middleware_redis_failure_fails_closed() -> None:
    app = _make_app()
    redis_client = _mock_redis_client()
    redis_client.available = True
    redis_client.incr_or_raise.side_effect = RedisUnavailableError("Redis down")

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 5
        resp = client.get("/api/v1/auth/login")
    assert resp.status_code == 503


def test_middleware_redis_required_unavailable_fails_closed() -> None:
    """Production requires Redis; if unavailable, fail closed (503)."""
    app = _make_app()
    redis_client = _mock_redis_client()
    redis_client.available = False

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 5
        mock_settings.return_value.app_env = "production"
        resp = client.get("/api/v1/auth/login")
    assert resp.status_code == 503


def test_middleware_in_memory_fallback_when_no_redis() -> None:
    """Without Redis configured, in-memory sliding window is used."""
    app = _make_app()
    app.add_middleware(RateLimitMiddleware)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 3
        mock_settings.return_value.app_env = "development"
        responses = [client.get("/api/v1/auth/login") for _ in range(5)]
    codes = [r.status_code for r in responses]
    assert 429 in codes
    assert 200 in codes


def test_middleware_in_memory_returns_retry_after() -> None:
    app = _make_app()
    app.add_middleware(RateLimitMiddleware)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 1
        mock_settings.return_value.app_env = "development"
        client.get("/api/v1/auth/login")
        resp = client.get("/api/v1/auth/login")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_middleware_redis_endpoint_isolation() -> None:
    """Different endpoints have independent Redis counters."""
    app = _make_app()
    redis_client = _mock_redis_client()
    redis_client.available = True

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 5
        mock_settings.return_value.rate_limit_intent_per_minute = 5

        # Login endpoint over limit.
        redis_client.incr_or_raise.return_value = 6
        login_resp = client.get("/api/v1/auth/login")
        assert login_resp.status_code == 429

        # Intent endpoint under limit.
        redis_client.incr_or_raise.return_value = 1
        intent_resp = client.get("/api/v1/intent/verify")
        assert intent_resp.status_code == 200


def test_middleware_redis_client_isolation() -> None:
    """Different clients have independent Redis counters."""
    app = _make_app()
    redis_client = _mock_redis_client()
    redis_client.available = True

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 5

        # First client over limit.
        redis_client.incr_or_raise.return_value = 6
        resp1 = client.get("/api/v1/auth/login", headers={"X-Forwarded-For": "1.1.1.1"})
        assert resp1.status_code == 429

        # Second client under limit.
        redis_client.incr_or_raise.return_value = 1
        resp2 = client.get("/api/v1/auth/login", headers={"X-Forwarded-For": "2.2.2.2"})
        assert resp2.status_code == 200


def test_middleware_x_forwarded_for_with_trusted_proxy() -> None:
    """When behind a trusted proxy, use the rightmost untrusted X-Forwarded-For IP."""
    app = _make_app()
    redis_client = _mock_redis_client()
    redis_client.available = True

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 1
        mock_settings.return_value.trusted_proxies = ["testclient"]

        # Request from trusted proxy with X-Forwarded-For chain.
        redis_client.incr_or_raise.return_value = 1
        resp = client.get(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": "1.1.1.1, testclient"},
        )
        assert resp.status_code == 200

        # Second request from same untrusted IP should be rate limited.
        redis_client.incr_or_raise.return_value = 2
        resp2 = client.get(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": "1.1.1.1, testclient"},
        )
        assert resp2.status_code == 429


def test_middleware_x_forwarded_for_without_trusted_proxy() -> None:
    """Without trusted proxies, X-Forwarded-For is ignored and direct IP is used."""
    app = _make_app()
    app.add_middleware(RateLimitMiddleware)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 1
        mock_settings.return_value.trusted_proxies = []

        # First request succeeds.
        resp = client.get("/api/v1/auth/login")
        assert resp.status_code == 200

        # Second request from same direct IP is rate limited, even with X-Forwarded-For.
        resp2 = client.get(
            "/api/v1/auth/login", headers={"X-Forwarded-For": "2.2.2.2"}
        )
        assert resp2.status_code == 429


def test_middleware_x_forwarded_for_all_trusted_falls_back_to_direct() -> None:
    """When all X-Forwarded-For IPs are trusted, fall back to direct client IP."""
    app = _make_app()
    app.add_middleware(RateLimitMiddleware)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 1
        mock_settings.return_value.trusted_proxies = ["testclient"]

        # First request succeeds.
        resp = client.get(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": "testclient, testclient"},
        )
        assert resp.status_code == 200

        # Second request from same direct IP is rate limited.
        resp2 = client.get(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": "testclient, testclient"},
        )
        assert resp2.status_code == 429


def test_get_client_ip_uses_x_forwarded_for_with_trusted_proxy() -> None:
    from starlette.requests import Request

    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.trusted_proxies = ["10.0.0.1"]
        request = Request(
            {
                "type": "http",
                "client": ("10.0.0.1", 1234),
                "headers": [[b"x-forwarded-for", b"1.1.1.1, 10.0.0.1"]],
            }
        )
        assert _get_client_ip(request) == "1.1.1.1"


def test_get_client_ip_ignores_x_forwarded_for_without_trusted_proxy() -> None:
    from starlette.requests import Request

    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.trusted_proxies = []
        request = Request(
            {
                "type": "http",
                "client": ("2.2.2.2", 1234),
                "headers": [[b"x-forwarded-for", b"1.1.1.1"]],
            }
        )
        assert _get_client_ip(request) == "2.2.2.2"


def test_get_client_ip_all_trusted_falls_back_to_client() -> None:
    from starlette.requests import Request

    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.trusted_proxies = ["10.0.0.1"]
        request = Request(
            {
                "type": "http",
                "client": ("10.0.0.1", 1234),
                "headers": [[b"x-forwarded-for", b"10.0.0.1"]],
            }
        )
        assert _get_client_ip(request) == "10.0.0.1"


def test_get_client_ip_no_x_forwarded_for_falls_back_to_client() -> None:
    from starlette.requests import Request

    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.trusted_proxies = ["10.0.0.1"]
        request = Request(
            {
                "type": "http",
                "client": ("10.0.0.1", 1234),
                "headers": [],
            }
        )
        assert _get_client_ip(request) == "10.0.0.1"
