"""Tests for database engine configuration branches."""

from app.infrastructure.persistence.database import _build_engine_kwargs


def test_build_engine_kwargs_sqlite_memory() -> None:
    kwargs = _build_engine_kwargs("sqlite:///:memory:")
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["connect_args"] == {"check_same_thread": False}
    assert kwargs["poolclass"].__name__ == "StaticPool"


def test_build_engine_kwargs_sqlite_file() -> None:
    kwargs = _build_engine_kwargs("sqlite:///./intentlock.db")
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["connect_args"] == {"check_same_thread": False}
    assert "poolclass" not in kwargs


def test_build_engine_kwargs_postgresql() -> None:
    kwargs = _build_engine_kwargs("postgresql+psycopg2://user:pass@localhost/db")
    assert kwargs["pool_pre_ping"] is True
    assert "connect_args" not in kwargs
    assert "poolclass" not in kwargs
