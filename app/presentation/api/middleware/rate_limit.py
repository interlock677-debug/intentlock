import time
from collections import defaultdict

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.infrastructure.config.settings import get_settings
from app.infrastructure.logging.audit_logger import log_security_event

RATE_LIMITS = {
    "/api/v1/auth/login": "rate_limit_login_per_minute",
    "/api/v1/auth/register": "rate_limit_register_per_minute",
    "/api/v1/intent/verify": "rate_limit_intent_per_minute",
}

request_counts: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def reset_rate_limits() -> None:
    """Clear all rate limit state (used in tests)."""
    request_counts.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiting middleware.

    Rate limiting is a DoS mitigation control, not a security boundary.
    If the rate limiter fails, requests are allowed through (fail-open)
    to preserve availability.
    """

    async def dispatch(self, request: Request, call_next):
        route = request.url.path
        limit_setting = RATE_LIMITS.get(route)
        if limit_setting:
            settings = get_settings()
            max_calls = int(getattr(settings, limit_setting, 60))
            window = 60  # seconds

            remote_addr = request.client.host if request.client else "unknown"
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
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                )
        return await call_next(request)
