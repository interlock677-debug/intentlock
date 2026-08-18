from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.exceptions.domain_errors import ApprovalError
from app.domain.models.intent import AgentActionDAG
from app.domain.services.hitl_queue import HITLQueue
from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.domain.services.policy_engine import PolicyEngine
from app.infrastructure.config.settings import Settings
from app.infrastructure.redis.client import RedisUnavailableError

# ---------- hitl_queue._decide expired branch ----------


@pytest.mark.asyncio
async def test_hitl_decide_expired_direct() -> None:
    """Approving an expired request fails and persists the expired status."""
    from sqlalchemy import select

    from app.infrastructure.persistence.database import get_db_session
    from app.infrastructure.persistence.models.approval_request_model import ApprovalRequestModel

    queue = HITLQueue(ttl_seconds=300)
    req_id = await queue.enqueue_request(intent_text="old", risk_score=0.5)
    # Set the entry to expire in the past.
    with get_db_session() as session:
        model = session.scalar(
            select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == req_id)
        )
        assert model is not None
        model.expires_at = datetime.now(tz=UTC) - timedelta(seconds=5)

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


# ---------- intent_evaluator sqlglot branches ----------


def test_intent_evaluator_parse_one_raises_and_returns_none() -> None:
    """sqlglot.parse_one raises ParseError -> pass; then None returned."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="run",
        reasoning_step="step",
        proposed_tool="sql_query",
        tool_arguments={"query": "not valid sql statement"},
    )
    # _inspect_destructive_sql: no regex match, sqlglot raises ParseError -> None.
    assert evaluator._inspect_destructive_sql(intent) is None


def test_intent_evaluator_parsed_deletion_with_where() -> None:
    """DELETE with WHERE: regex doesn't match, but parser detects it."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="clean row",
        reasoning_step="run SQL",
        proposed_tool="sql_query",
        tool_arguments={"query": "DELETE FROM users WHERE id = 5"},
    )
    result = evaluator.evaluate(intent)
    assert not result.is_valid
    assert "Destructive SQL" in result.reason or "Tool argument validation failed" in result.reason


def test_intent_evaluator_ast_parse_exception_returns_false() -> None:
    """_contains_polyglot_payload: sqlglot fails, ast fails -> return False."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="just some ordinary words here",
        reasoning_step="step",
        proposed_tool="bash",
        tool_arguments={},
    )
    assert evaluator._contains_polyglot_payload(intent) is False


# ---------- policy_engine simple yaml fallback ----------


def test_policy_engine_simple_yaml_fallback() -> None:
    """_parse_simple_yaml handles nested blocked_patterns when yaml is None."""
    yaml_file = Path("config/policies.yaml")
    if not yaml_file.exists():
        pytest.skip("config/policies.yaml not present")
    with patch("app.domain.services.policy_engine.yaml", None):
        engine = PolicyEngine.from_file(yaml_file)
    assert isinstance(engine.score_threshold, float)


def test_policy_engine_simple_yaml_blocked_patterns(tmp_path: Path) -> None:
    yaml_file = tmp_path / "p.yaml"
    yaml_file.write_text(
        "score_threshold: 0.4\nblocked_patterns:\n  - drop\n  - truncate\n",
        encoding="utf-8",
    )
    with patch("app.domain.services.policy_engine.yaml", None):
        engine = PolicyEngine.from_file(yaml_file)
    assert engine.score_threshold == 0.4
    assert engine.blocked_patterns == ["drop", "truncate"]


# ---------- settings cors string parse + placeholder ----------


def test_settings_cors_origins_string_list() -> None:
    with patch.dict(
        "os.environ",
        {"CORS_ORIGINS": '["https://a.com"]'},
        clear=False,
    ):
        settings = Settings(_env_file=None)
    assert settings.cors_origins == ["https://a.com"]


def test_settings_rejects_change_me_secret() -> None:
    with pytest.raises(ValueError):
        Settings(jwt_secret_key="change-me-12345678901234567890", _env_file=None)


# ---------- audit_logger handler re-init ----------


def test_audit_logger_handlers_initialized() -> None:
    from app.infrastructure.logging import audit_logger

    assert audit_logger.logger.handlers


# ---------- auth dependency AuthenticationError -> 401 ----------


def test_auth_dependency_invalid_token_returns_401() -> None:
    from fastapi import Depends

    from app.presentation.api.dependencies.auth import get_current_user_id

    app = FastAPI()

    @app.get("/whoami")
    async def whoami(user_id: object = Depends(get_current_user_id)) -> object:
        return {"id": user_id}

    client = TestClient(app)
    resp = client.get("/whoami", headers={"Authorization": "Bearer invalid.token"})
    assert resp.status_code == 401


# ---------- security dependencies redis path ----------


def test_get_redis_client_when_configured() -> None:
    from app.presentation.api.dependencies import security

    security.get_redis_client.cache_clear()
    try:
        with patch.object(security, "get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379/0"
            mock_settings.return_value.redis_enabled = True
            client = security.get_redis_client()
        assert client.available is False  # real Redis unavailable in tests
    finally:
        security.get_redis_client.cache_clear()


def test_get_nonce_store_with_redis_available() -> None:
    from app.presentation.api.dependencies import security

    security.get_nonce_store.cache_clear()
    try:
        with patch.object(security, "get_redis_client") as mock_redis:
            mock_client = MagicMock()
            mock_client.available = True
            mock_redis.return_value = mock_client
            store = security.get_nonce_store()
        assert store is not None
    finally:
        security.get_nonce_store.cache_clear()


def test_production_nonce_store_fails_closed_when_redis_is_unavailable() -> None:
    from app.presentation.api.dependencies import security

    security.get_nonce_store.cache_clear()
    try:
        with (
            patch.object(security, "get_redis_client") as mock_redis,
            patch.object(security, "get_settings") as mock_settings,
        ):
            mock_client = MagicMock()
            mock_client.available = False
            mock_client.set_nx.side_effect = RedisUnavailableError("Redis is unavailable")
            mock_redis.return_value = mock_client
            mock_settings.return_value.app_env = "production"
            store = security.get_nonce_store()

        assert store.consume("nonce", 60) is False
    finally:
        security.get_nonce_store.cache_clear()


# ---------- rate_limit 429 ----------


def test_rate_limit_exceeded_returns_429() -> None:
    from fastapi import FastAPI

    from app.presentation.api.middleware.rate_limit import (
        RateLimitMiddleware,
        reset_rate_limits,
    )

    app = FastAPI()

    @app.get("/api/v1/auth/login")
    async def login() -> dict[str, str]:
        return {"token": "ok"}

    app.add_middleware(RateLimitMiddleware)
    reset_rate_limits()

    client = TestClient(app)
    with patch("app.presentation.api.middleware.rate_limit.get_settings") as mock_settings:
        mock_settings.return_value.rate_limit_login_per_minute = 3
        responses = [client.get("/api/v1/auth/login") for _ in range(5)]
    codes = [r.status_code for r in responses]
    assert 429 in codes
    assert 200 in codes
