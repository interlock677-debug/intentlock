from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import init_db
from app.presentation.api.middleware.correlation import CorrelationIdMiddleware
from app.presentation.api.middleware.exception_handler import register_exception_handlers
from app.presentation.api.middleware.rate_limit import RateLimitMiddleware
from app.presentation.api.middleware.request_size_limit import RequestSizeLimitMiddleware
from app.presentation.api.middleware.security_headers import SecurityHeadersMiddleware
from app.presentation.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="4.0.0",
        description="Enterprise-grade dynamic proof-of-intent authorization gateway for AI agents.",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        RequestSizeLimitMiddleware, max_bytes=settings.request_max_body_bytes
    )
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(application)
    application.include_router(api_v1_router, prefix="/api/v1")

    return application


app = create_app()
