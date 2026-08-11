import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions.domain_errors import (
    ApprovalError,
    AuthenticationError,
    DomainError,
    ExecutionTokenError,
    PolicyViolationError,
    WebhookError,
)

logger = logging.getLogger("intentlock.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers.

    Prevents internal stack traces from leaking through API responses.
    """

    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        if isinstance(exc, (AuthenticationError, ExecutionTokenError)):
            logger.warning("Security error: %s", exc)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": str(exc)},
            )
        if isinstance(exc, (PolicyViolationError, WebhookError)):
            logger.warning("Policy error: %s", exc)
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": str(exc)},
            )
        if isinstance(exc, ApprovalError):
            logger.warning("Approval error: %s", exc)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": str(exc)},
            )
        logger.error("Domain error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        logger.exception(
            "Unhandled exception (correlation_id=%s): %s",
            correlation_id,
            exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error.",
                "correlation_id": correlation_id,
            },
        )
