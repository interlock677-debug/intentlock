import asyncio

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.user import User
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
            id=__import__("uuid").uuid4(),
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
    return asyncio.run(_create_user("intent-test@example.com", role="viewer"))


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_intent_verify_returns_ephemeral_token(client: TestClient, auth_token: str) -> None:
    payload = {
        "user_prompt": "Search for user records",
        "agent_id": "agent-123",
        "reasoning_step": "Execute search",
        "proposed_tool": "search",
        "tool_arguments": {"query": "SELECT * FROM users LIMIT 10"},
    }

    response = client.post("/api/v1/intent/verify", json=payload, headers=_auth_headers(auth_token))

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["ephemeral_token"]
    assert body["confidence_score"] > 0.9


def test_intent_verify_rejects_destructive_sql(client: TestClient, auth_token: str) -> None:
    payload = {
        "user_prompt": "Run a harmful query",
        "agent_id": "agent-123",
        "reasoning_step": "Cleanup database",
        "proposed_tool": "execute_sql",
        "tool_arguments": {"query": "DROP TABLE users;"},
    }

    response = client.post("/api/v1/intent/verify", json=payload, headers=_auth_headers(auth_token))

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert (
        "Destructive SQL" in detail
        or "Tool argument validation failed" in detail
        or "Deny execution of dangerous tools" in detail
    )


def test_intent_verify_rejects_overlimit_transfer(client: TestClient, auth_token: str) -> None:
    payload = {
        "user_prompt": "Transfer no more than $100",
        "agent_id": "agent-123",
        "reasoning_step": "Send payment",
        "proposed_tool": "transfer_funds",
        "tool_arguments": {"amount": 150, "recipient": "vendor-abc"},
    }

    response = client.post("/api/v1/intent/verify", json=payload, headers=_auth_headers(auth_token))

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert (
        "exceeds the prompt limit" in detail
        or "Require human approval for financial transfer tools" in detail
    )
