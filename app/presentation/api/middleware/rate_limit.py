import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.infrastructure.config.settings import get_settings
from app.infrastructure.logging.audit_logger import log_security_event
from app.infrastructure.redis.client import RedisClient, RedisUnavailableError
from app.infrastructure.redis.rate_limiter import RedisRateLimiter

RATE_LIMITS = {
    "/api/v1/auth/login": "rate_limit_login_per_minute",
    "/api/v1/auth/register": "rate_limit_register_per_minute",
    "/api/v1/intent/verify": "rate_limit_intent_per_minute",
}

WINDOW_SECONDS = 60

request_counts: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def reset_rate_limits() -> None:
    """Clear all rate limit state (used in tests)."""
    request_counts.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiting middleware with Redis distribution.

    When Redis is available, rate limiting is distributed across all
    application instances using atomic Redis counters.  When Redis is not
    configured (development/test), an in-memory sliding window is used.

    Security behavior:
        - If Redis is required (production) but unavailable, requests are
          rejected with 503 (fail-closed) rather than silently becoming
          unlimited.
        - If Redis is not configured at all, the in-memory fallback is used.
        - 429 responses include a ``Retry-After`` header.
    """

    def __init__(
        self,
        app: object,
        *,
        redis_client: RedisClient | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._redis_client = redis_client
        self._redis_limiter: RedisRateLimiter | None = None
        self._redis_checked = False

    def _get_redis_limiter(self) -> RedisRateLimiter | None:
        """Return a Redis-backed limiter if Redis is available.

        If Redis is required (production) but unavailable, returns a
        sentinel that causes fail-closed behavior via ``_redis_required``.
        """
        if not self._redis_checked:
            self._redis_checked = True
            client = self._redis_client
            if client is None:
                from app.presentation.api.dependencies.security import get_redis_client

                client = get_redis_client()
            if client is not None and client.available:
                self._redis_limiter = RedisRateLimiter(client, window_seconds=WINDOW_SECONDS)
            else:
                settings = get_settings()
                if settings.app_env == "production":
                    self._redis_required = True
        return self._redis_limiter

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        route = request.url.path
        limit_setting = RATE_LIMITS.get(route)
        if limit_setting:
            settings = get_settings()
            max_calls = int(getattr(settings, limit_setting, 60))
            window = WINDOW_SECONDS

            remote_addr = request.client.host if request.client else "unknown"

            redis_limiter = self._get_redis_limiter()
            if redis_limiter is not None:
                # Distributed rate limiting via Redis.
                try:
                    allowed, retry_after = redis_limiter.check(route, remote_addr, max_calls)
                except RedisUnavailableError:
                    # Redis failed mid-operation.  Fail closed to avoid
                    # silently becoming unlimited.
                    log_security_event(
                        "rate_limit_redis_failure",
                        route=route,
                        remote_addr=remote_addr,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={"detail": "Rate limiter unavailable"},
                    )
                if not allowed:
                    log_security_event(
                        "rate_limit_exceeded",
                        route=route,
                        remote_addr=remote_addr,
                    )
                    headers = {}
                    if retry_after is not None:
                        headers["Retry-After"] = str(retry_after)
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded"},
                        headers=headers,
                    )
                return await call_next(request)

            if getattr(self, "_redis_required", False):
                # Redis is required (production) but unavailable at startup.
                log_security_event(
                    "rate_limit_redis_unavailable",
                    route=route,
                    remote_addr=remote_addr,
                )
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": "Rate limiter unavailable"},
                )

            # In-memory sliding-window fallback (development/test).
            now = time.time()
            window_requests = [
                timestamp
                for timestamp in request_counts[route][remote_addr]
                if now - timestamp < window
            ]
            window_requests.append(now)
            request_counts[route][remote_addr] = window_requests

            if len(window_requests) > max_calls:
                log_security_event(
                    "rate_limit_exceeded",
                    route=route,
                    remote_addr=remote_addr,
                )
                retry_after = max(1, int(window - (now % window)))
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)