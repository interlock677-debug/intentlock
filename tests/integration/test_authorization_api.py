import asyncio
import json
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.user import User
from app.domain.services.authorization_service import AuthorizationService
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService


async def _create_user(email: str, role: str = "viewer") -> str:
    settings = get_settings()
    session = SessionLocal()
    try:
        repo = SQLAlchemyUserRepository(session)
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=BcryptPasswordHasher(rounds=4).hash("Password123!"),
            is_active=True,
            created_at=__import__("datetime").datetime.now(tz=__import__("datetime").UTC),
            role=role,
            tenant_id="test-tenant",
        )
        saved = await repo.save(user)
        token = JWTTokenService(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_access_token_expire_minutes,
            clock_skew_seconds=settings.jwt_clock_skew_seconds,
        ).create_access_token(user_id=saved.id, email=saved.email)
        session.commit()
        return token
    finally:
        session.close()


@pytest.fixture
def auth_token(client: TestClient) -> str:
    return asyncio.run(_create_user("authz-test@example.com", role="viewer"))


def _make_authz_service(**overrides: object) -> AuthorizationService:
    defaults = {
        "authorization_denied_tools": [],
        "authorization_hitl_tools": [],
        "authorization_require_tenant": False,
    }
    defaults.update(overrides)

    class _Settings:
        pass

    s = _Settings()
    for key, value in defaults.items():
        setattr(s, key, value)
    return AuthorizationService(settings=s)


@pytest.mark.asyncio
async def test_authorized_action_permitted(client: TestClient, auth_token: str) -> None:
    response = client.post(
        "/api/v1/intent/verify",
        json={
            "user_prompt": "normal prompt",
            "agent_id": "agent-1",
            "reasoning_step": "normal",
            "proposed_tool": "search",
            "tool_arguments": {"query": "test"},
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["ephemeral_token"]


@pytest.mark.asyncio
async def test_authorization_deny_returns_403(client: TestClient, auth_token: str) -> None:
    mock_service = _make_authz_service(
        authorization_denied_tools=["restricted_tool"],
    )
    with patch("app.presentation.api.v1.routes.intent._authz_service", mock_service):
        response = client.post(
            "/api/v1/intent/verify",
            json={
                "user_prompt": "normal prompt",
                "agent_id": "agent-1",
                "reasoning_step": "normal",
                "proposed_tool": "restricted_tool",
                "tool_arguments": {"query": "test"},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert response.status_code == 403
    assert "restricted_tool" in response.json()["detail"]


@pytest.mark.asyncio
async def test_authorization_require_hitl_returns_403(client: TestClient, auth_token: str) -> None:
    mock_service = _make_authz_service(
        authorization_hitl_tools=["high_risk_tool"],
    )
    with patch("app.presentation.api.v1.routes.intent._authz_service", mock_service):
        response = client.post(
            "/api/v1/intent/verify",
            json={
                "user_prompt": "normal prompt",
                "agent_id": "agent-1",
                "reasoning_step": "normal",
                "proposed_tool": "high_risk_tool",
                "tool_arguments": {"query": "test"},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert response.status_code == 403
    assert "requires human approval" in response.json()["detail"]


@pytest.mark.asyncio
async def test_authorization_audit_event_written_on_deny(
    client: TestClient, auth_token: str,
) -> None:
    mock_service = _make_authz_service(
        authorization_denied_tools=["blocked_tool"],
    )
    with patch("app.presentation.api.v1.routes.intent._authz_service", mock_service):
        client.post(
            "/api/v1/intent/verify",
            json={
                "user_prompt": "normal prompt",
                "agent_id": "agent-1",
                "reasoning_step": "normal",
                "proposed_tool": "blocked_tool",
                "tool_arguments": {"query": "test"},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    from app.infrastructure.logging.audit_logger import LOG_PATH

    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    events = [json.loads(line) for line in lines if line.strip()]
    auth_events = [e for e in events if e.get("event_type") == "intent_verification"]
    assert len(auth_events) >= 1
    last_event = auth_events[-1]
    assert last_event["verification_status"] == "AUTH_DENIED"


@pytest.mark.asyncio
async def test_authorization_audit_event_written_on_require_hitl(
    client: TestClient, auth_token: str,
) -> None:
    mock_service = _make_authz_service(
        authorization_hitl_tools=["hitl_tool"],
    )
    with patch("app.presentation.api.v1.routes.intent._authz_service", mock_service):
        client.post(
            "/api/v1/intent/verify",
            json={
                "user_prompt": "normal prompt",
                "agent_id": "agent-1",
                "reasoning_step": "normal",
                "proposed_tool": "hitl_tool",
                "tool_arguments": {"query": "test"},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    from app.infrastructure.logging.audit_logger import LOG_PATH

    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    events = [json.loads(line) for line in lines if line.strip()]
    auth_events = [e for e in events if e.get("event_type") == "intent_verification"]
    assert len(auth_events) >= 1
    last_event = auth_events[-1]
    assert last_event["verification_status"] == "AUTH_REQUIRE_HITL"


def test_policy_bypass_via_alternate_endpoint_still_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/intent/verify", json={})
    assert response.status_code == 401
