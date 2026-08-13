from fastapi import APIRouter
from sqlalchemy import text

from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import engine
from app.infrastructure.redis.client import RedisClient

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def readiness_check() -> dict[str, str]:
    """Readiness probe: verifies database and Redis connectivity."""
    settings = get_settings()

    db_status = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    redis_status = "disabled"
    if settings.redis_url and settings.redis_enabled:
        redis_client = RedisClient(settings.redis_url)
        redis_status = "ok" if redis_client.available else "unhealthy"

    redis_required = bool(settings.redis_url and settings.redis_enabled)
    ready = db_status == "ok" and (not redis_required or redis_status == "ok")
    return {
        "status": "ready" if ready else "not_ready",
        "db": db_status,
        "redis": redis_status,
    }
