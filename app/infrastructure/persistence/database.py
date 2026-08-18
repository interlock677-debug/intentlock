from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.config.settings import get_settings


def _build_engine_kwargs(database_url: str) -> dict[str, object]:
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    if database_url == "sqlite:///:memory:":
        kwargs["poolclass"] = StaticPool
    return kwargs


settings = get_settings()
_engine_kwargs = _build_engine_kwargs(settings.database_url)
engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


def init_db() -> None:
    """Create database tables."""
    # Import models so metadata is populated before create_all.
    from app.infrastructure.persistence.models import (  # noqa: F401
        ApprovalRequestModel,
        AuditEventModel,
        ExecutionTokenModel,
        UserModel,
    )

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[Session, None]:
    """Async wrapper for database session lifecycle."""
    with get_db_session() as session:
        yield session
