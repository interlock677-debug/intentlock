import asyncio
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.user import User
from app.domain.services.central_policy_engine import CentralPolicyEngine
from app.domain.services.policy_store import PolicyStore
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
    return asyncio.run(_create_user("policy-test@example.com", role="viewer"))


def _make_policy_engine(**overrides: object) -> CentralPolicyEngine:
    store = PolicyStore()
    store.load("1", {
        "policy_version": "1",
        "default_effect": "allow",
        "rules": [
            {
                "id": "deny-test-tool",
                "version": "1",
                "effect": "deny",
                "description": "Deny test tool",
                "match": {"tool": "restricted_tool"},
                "priority": 100,
            },
            {
                "id": "hitl-test-tool",
                "version": "1",
                "effect": "require_hitl",
                "description": "HITL for test tool",
                "match": {"tool": "sensitive_tool"},
                "priority": 50,
            },
        ],
    })
    return CentralPolicyEngine(store)


@pytest.mark.asyncio
async def test_policy_deny_blocks_intent(client: TestClient, auth_token: str) -> None:
    mock_engine = _make_policy_engine()
    with patch("app.presentation.api.v1.routes.intent._policy_engine", mock_engine):
        response = client.post(
            "/api/v1/intent/verify",
            json={
                "user_prompt": "normal",
                "agent_id": "agent-1",
                "reasoning_step": "normal",
                "proposed_tool": "restricted_tool",
                "tool_arguments": {},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert response.status_code == 403
    assert "Deny test tool" in response.json()["detail"]


@pytest.mark.asyncio
async def test_policy_require_hitl_blocks_intent(client: TestClient, auth_token: str) -> None:
    mock_engine = _make_policy_engine()
    with patch("app.presentation.api.v1.routes.intent._policy_engine", mock_engine):
        response = client.post(
            "/api/v1/intent/verify",
            json={
                "user_prompt": "normal",
                "agent_id": "agent-1",
                "reasoning_step": "normal",
                "proposed_tool": "sensitive_tool",
                "tool_arguments": {},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert response.status_code == 403
    assert "HITL for test tool" in response.json()["detail"]


@pytest.mark.asyncio
async def test_policy_allow_permits_intent(client: TestClient, auth_token: str) -> None:
    mock_engine = _make_policy_engine()
    with patch("app.presentation.api.v1.routes.intent._policy_engine", mock_engine):
        response = client.post(
            "/api/v1/intent/verify",
            json={
                "user_prompt": "safe search query",
                "agent_id": "agent-1",
                "reasoning_step": "search",
                "proposed_tool": "safe_tool",
                "tool_arguments": {"query": "test"},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["ephemeral_token"]
