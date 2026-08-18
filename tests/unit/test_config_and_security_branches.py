from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.dto.auth import LoginRequest, RegisterRequest
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.get_current_user import GetCurrentUserUseCase
from app.domain.exceptions.domain_errors import (
    ApprovalError,
    InactiveUserError,
    UserNotFoundError,
)
from app.domain.models.intent import AgentActionDAG
from app.domain.services.hitl_queue import HITLQueue
from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.domain.services.policy_engine import PolicyEngine
from app.domain.services.velocity_tracker import VelocityTracker
from app.infrastructure.config.settings import Settings
from app.infrastructure.redis.client import RedisClient

# ---------- DTO password validation ----------

def test_register_request_rejects_missing_special_char() -> None:
    with pytest.raises(ValueError):
        RegisterRequest(email="user@example.com", password="Password123")


def test_register_request_rejects_missing_uppercase() -> None:
    with pytest.raises(ValueError):
        RegisterRequest(email="user@example.com", password="password123!")


def test_register_request_rejects_missing_digit() -> None:
    with pytest.raises(ValueError):
        RegisterRequest(email="user@example.com", password="Passwordabc!")


def test_register_request_valid() -> None:
    req = RegisterRequest(email="user@example.com", password="Password123!")
    assert str(req.email) == "user@example.com"


# ---------- Use cases ----------

@pytest.mark.asyncio
async def test_authenticate_inactive_user() -> None:
    repo = AsyncMock()
    hasher = MagicMock()
    hasher.verify.return_value = True
    tokens = MagicMock()
    user = MagicMock()
    user.is_active = False
    user.hashed_password = "hash"
    repo.get_by_email.return_value = user

    uc = AuthenticateUserUseCase(repo, hasher, tokens)
    with pytest.raises(InactiveUserError):
        await uc.execute(LoginRequest(email="a@b.com", password="Password1!"))


@pytest.mark.asyncio
async def test_get_current_user_not_found() -> None:
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    uc = GetCurrentUserUseCase(repo)
    with pytest.raises(UserNotFoundError):
        await uc.execute(uuid4())


# ---------- HITL queue: expired decision ----------

@pytest.mark.asyncio
async def test_hitl_decision_on_expired_entry() -> None:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.infrastructure.persistence.database import get_db_session
    from app.infrastructure.persistence.models.approval_request_model import ApprovalRequestModel

    queue = HITLQueue(ttl_seconds=1)
    req_id = await queue.enqueue_request(intent_text="old", risk_score=0.5)
    # Force the entry into the past.
    with get_db_session() as session:
        model = session.scalar(
            select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == req_id)
        )
        assert model is not None
        model.expires_at = datetime.now(tz=UTC) - timedelta(seconds=5)

    # approve_request on an expired request fails and persists the expired status.
    with pytest.raises(ApprovalError) as exc:
        await queue.approve_request(req_id)
    assert "has expired" in str(exc.value)
    # The request must have been persisted with status expired.
    with get_db_session() as session:
        model = session.scalar(
            select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == req_id)
        )
        assert model is not None
        assert model.status == "expired"


# ---------- Intent evaluator remaining branches ----------

def test_intent_evaluator_parsed_non_destructive_sql_passes() -> None:
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="agent-1",
        user_prompt="Run a query",
        reasoning_step="Query the database",
        proposed_tool="sql_query",
        tool_arguments={"query": "SELECT * FROM users"},
    )
    result = evaluator.evaluate(intent)
    # Valid SQL text parses via sqlglot (line 87 hit) and is not destructive.
    assert result.is_valid


def test_intent_evaluator_prompt_limit_without_transfer_amount() -> None:
    evaluator = IntentEvaluatorService()
    # Prompt limit exists and tool is a transfer action, but no amount found.
    intent = AgentActionDAG(
        agent_id="agent-1",
        user_prompt="Send payment up to $100",
        reasoning_step="Send payment",
        proposed_tool="transfer_funds",
        tool_arguments={"recipient": "alice"},
    )
    result = evaluator.evaluate(intent)
    assert result.is_valid


def test_intent_evaluator_transfer_amount_from_string_value() -> None:
    evaluator = IntentEvaluatorService()
    # amount key is "total" with a dollar-prefixed string value.
    intent = AgentActionDAG(
        agent_id="agent-1",
        user_prompt="Send payment up to $1000",
        reasoning_step="Send payment",
        proposed_tool="transfer_funds",
        tool_arguments={"total": "$900"},
    )
    result = evaluator.evaluate(intent)
    assert result.is_valid


def test_intent_evaluator_ast_parses_python() -> None:
    evaluator = IntentEvaluatorService()
    # Python expression text that fails sqlglot but parses via ast.
    intent = AgentActionDAG(
        agent_id="agent-1",
        user_prompt="1 + 1",
        reasoning_step="step",
        proposed_tool="bash",
        tool_arguments={},
    )
    result = evaluator.evaluate(intent)
    assert not result.is_valid
    assert "Polyglot or shell payload" in result.reason


# ---------- Policy engine ----------

def test_policy_engine_from_file_with_yaml(tmp_path: Path) -> None:
    yaml_file = tmp_path / "policy.yaml"
    yaml_file.write_text(
        "score_threshold: 0.7\n"
        "blocked_patterns:\n"
        "  - dangerous\n",
        encoding="utf-8",
    )
    engine = PolicyEngine.from_file(yaml_file)
    assert engine.score_threshold == 0.7
    assert engine.blocked_patterns == ["dangerous"]


def test_policy_engine_simple_yaml_key_value_parse(tmp_path: Path) -> None:
    yaml_file = tmp_path / "simple.yaml"
    yaml_file.write_text(
        "score_threshold: 0.5\n"
        "other_key: value\n",
        encoding="utf-8",
    )
    with patch("app.domain.services.policy_engine.yaml", None):
        payload = PolicyEngine._parse_simple_yaml(yaml_file)
    assert payload["score_threshold"] == "0.5"
    assert payload["other_key"] == "value"


def test_policy_engine_missing_file_defaults(tmp_path: Path) -> None:
    engine = PolicyEngine.from_file(tmp_path / "does-not-exist.yaml")
    assert engine.score_threshold == 0.5
    assert engine.blocked_patterns == []


# ---------- Velocity tracker pruning ----------

def test_velocity_tracker_prunes_old_timestamps() -> None:
    tracker = VelocityTracker(window_seconds=1, max_requests=10)
    tracker.record(scope="agent", value=1.0)
    # Prepend two stale timestamps so they are at the front of the deque.
    old_time = time.monotonic() - 5
    window = tracker._windows["agent"]
    window.request_timestamps.appendleft(old_time)
    window.request_timestamps.appendleft(old_time - 1)
    state = tracker.get_state("agent")
    assert state["request_count"] == 1  # old timestamps pruned, fresh one remains


def test_velocity_tracker_prune_in_get_state() -> None:
    tracker = VelocityTracker(window_seconds=1, max_requests=10, max_cumulative_value=100.0)
    tracker.record(scope="s1", value=5.0)
    # Prepend a stale timestamp so it is at the front and pruned in get_state.
    old_time = time.monotonic() - 10
    window = tracker._windows["s1"]
    window.request_timestamps.appendleft(old_time)
    state = tracker.get_state("s1")
    assert state["request_count"] == 1


# ---------- Redis client incr without ex ----------

def test_redis_client_incr_without_expiry() -> None:
    client = RedisClient(None, enabled=False)
    mock_redis = MagicMock()
    client._client = mock_redis
    client._enabled = True
    mock_redis.incr.return_value = 3
    assert client.incr("key") == 3
    mock_redis.expire.assert_not_called()


# ---------- Config settings ----------

def test_settings_cors_origins_parses_string() -> None:
    with patch.dict(
        "os.environ",
        {"CORS_ORIGINS": '["http://a.com", "http://b.com"]'},
        clear=False,
    ):
        settings = Settings(_env_file=None)
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_settings_cors_origins_returns_empty_for_other_types() -> None:
    settings = Settings(_env_file=None)
    settings = settings.__class__(cors_origins=42)  # type: ignore[call-arg]
    assert settings.cors_origins == []


def test_settings_rejects_placeholder_secret() -> None:
    with pytest.raises(ValueError):
        Settings(jwt_secret_key="change-me-invalid", _env_file=None)


def test_settings_enforces_redis_for_production() -> None:
    with pytest.raises(ValueError):
        Settings(
            app_env="production",
            jwt_secret_key="a-very-long-production-secret-key-2026-abcdefgh",
            redis_url=None,
            database_url="postgresql+psycopg2://intentlock:secret@db:5432/intentlock",
            _env_file=None,
        )


def test_settings_allows_production_with_redis() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret_key="a-very-long-production-secret-key-2026-abcdefgh",
        redis_url="redis://localhost:6379/0",
        database_url="postgresql+psycopg2://intentlock:secret@db:5432/intentlock",
        _env_file=None,
    )
    assert settings.app_env == "production"
    assert settings.redis_url == "redis://localhost:6379/0"


def test_settings_rejects_disabled_redis_in_production() -> None:
    with pytest.raises(ValueError, match="cannot be disabled"):
        Settings(
            app_env="production",
            jwt_secret_key="a-very-long-production-secret-key-2026-abcdefgh",
            database_url="postgresql+psycopg2://intentlock:secret@db:5432/intentlock",
            redis_url="redis://localhost:6379/0",
            redis_enabled=False,
            _env_file=None,
        )


def test_settings_rejects_sqlite_in_production() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings(
            app_env="production",
            jwt_secret_key="a-very-long-production-secret-key-2026-abcdefgh",
            redis_url="redis://localhost:6379/0",
            _env_file=None,
        )


def test_settings_rejects_default_secret_in_non_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    # conftest.py sets JWT_SECRET_KEY globally via os.environ.setdefault, which
    # BaseSettings treats as an explicitly-configured value. To truly exercise
    # the "not configured" security path we must clear the env var first.
    # monkeypatch restores it automatically so other tests are unaffected.
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="configured explicitly"):
        Settings(
            app_env="staging",
            _env_file=None,
        )


# ---------- Database session rollback + async wrapper ----------

@pytest.mark.asyncio
async def test_async_db_session_wrapper() -> None:
    from app.infrastructure.persistence.database import get_async_db_session

    async with get_async_db_session() as session:
        assert session is not None


def test_db_session_rollback_on_error() -> None:
    from app.infrastructure.persistence import database

    original = database.SessionLocal
    fake_session = MagicMock()
    fake_session.__enter__.return_value = fake_session
    fake_session.commit.side_effect = RuntimeError("boom")
    database.SessionLocal = MagicMock(return_value=fake_session)
    try:
        with pytest.raises(RuntimeError), database.get_db_session():
            raise RuntimeError("nope")
    finally:
        database.SessionLocal = original
    fake_session.rollback.assert_called_once()
    fake_session.close.assert_called_once()


# ---------- Repository update branch ----------

@pytest.mark.asyncio
async def test_repository_updates_existing_user(db_session) -> None:

    from app.domain.entities.user import User
    from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
        SQLAlchemyUserRepository,
    )

    repo = SQLAlchemyUserRepository(db_session)
    existing = await repo.save(
        User(
            id=uuid4(),
            email="a@b.com",
            hashed_password="hash1",
            is_active=True,
            created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            tenant_id="test-tenant",
        )
    )
    updated = await repo.save(
        User(
            id=existing.id,
            email="a@b.com",
            hashed_password="hash2",
            is_active=False,
            created_at=existing.created_at,
            tenant_id="test-tenant",
        )
    )
    assert updated.hashed_password == "hash2"
    assert updated.is_active is False


def test_settings_trusted_proxies_parses_string() -> None:
    settings = Settings(
        trusted_proxies="10.0.0.1, 127.0.0.1",
        _env_file=None,
    )
    assert settings.trusted_proxies == ["10.0.0.1", "127.0.0.1"]


def test_settings_trusted_proxies_returns_empty_for_invalid_type() -> None:
    settings = Settings(
        trusted_proxies=42,  # type: ignore[call-arg]
        _env_file=None,
    )
    assert settings.trusted_proxies == []
