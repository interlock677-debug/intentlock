import asyncio

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


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_execute_endpoint_rejects_replay(client: TestClient) -> None:
    """A token used once must be rejected on second use."""
    token = asyncio.run(
        _create_user("replay-test@example.com")
    )

    verify_response = client.post(
        "/api/v1/intent/verify",
        json={
            "user_prompt": "Search for user records",
            "agent_id": "agent-123",
            "reasoning_step": "Execute search",
            "proposed_tool": "search",
            "tool_arguments": {"query": "SELECT * FROM users LIMIT 10"},
        },
        headers=_auth_headers(token),
    )
    assert verify_response.status_code == 200
    token_data = verify_response.json()
    execution_token = token_data["ephemeral_token"]
    assert execution_token

    # First execution should succeed
    execute_response = client.post(
        "/api/v1/intent/execute",
        json={"execution_token": execution_token},
        headers=_auth_headers(token),
    )
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == "executed"

    # Replay must be rejected
    replay_response = client.post(
        "/api/v1/intent/execute",
        json={"execution_token": execution_token},
        headers=_auth_headers(token),
    )
    assert replay_response.status_code == 401


def test_execute_endpoint_rejects_invalid_token(client: TestClient) -> None:
    token = asyncio.run(
        _create_user("invalid-token-test@example.com")
    )
    response = client.post(
        "/api/v1/intent/execute",
        json={"execution_token": "invalid-token"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 401


def test_jwks_endpoint_returns_public_key(client: TestClient) -> None:
    response = client.get("/api/v1/.well-known/jwks.json")
    assert response.status_code == 200
    body = response.json()
    assert "keys" in body
    assert len(body["keys"]) == 1
    assert body["keys"][0]["kty"] == "OKP"


def test_execute_endpoint_rejects_subject_mismatch(client: TestClient) -> None:
    """An execution token must be used by the same user who verified the intent."""
    token_a = asyncio.run(
        _create_user("subject-a@example.com")
    )
    token_b = asyncio.run(
        _create_user("subject-b@example.com")
    )

    verify_response = client.post(
        "/api/v1/intent/verify",
        json={
            "user_prompt": "Search for user records",
            "agent_id": "agent-123",
            "reasoning_step": "Execute search",
            "proposed_tool": "search",
            "tool_arguments": {"query": "SELECT * FROM users LIMIT 10"},
        },
        headers=_auth_headers(token_a),
    )
    assert verify_response.status_code == 200
    execution_token = verify_response.json()["ephemeral_token"]

    # Attempting to execute with a different user's bearer token must fail.
    execute_response = client.post(
        "/api/v1/intent/execute",
        json={"execution_token": execution_token},
        headers=_auth_headers(token_b),
    )
    assert execute_response.status_code == 403
    assert "subject" in execute_response.json()["detail"].lower()
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "not_ready"}
    assert body["db"] in {"ok", "unhealthy"}
