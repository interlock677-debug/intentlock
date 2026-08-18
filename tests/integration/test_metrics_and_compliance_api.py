import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService


async def _create_user(email: str, role: str = "admin") -> str:
    settings = get_settings()
    session = SessionLocal()
    try:
        repo = SQLAlchemyUserRepository(session)
        user = __import__("app.domain.entities.user", fromlist=["User"]).User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=BcryptPasswordHasher(rounds=4).hash("Password123!"),
            is_active=True,
            created_at=__import__("datetime").datetime.now(tz=__import__("datetime").UTC),
            role=role,
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
def admin_token(client: TestClient) -> str:
    return asyncio.run(_create_user("metrics-admin@example.com", role="admin"))


@pytest.fixture
def viewer_token(client: TestClient) -> str:
    return asyncio.run(_create_user("metrics-viewer@example.com", role="viewer"))


@pytest.mark.asyncio
async def test_metrics_security_endpoint_returns_snapshot(
    client: TestClient, admin_token: str,
) -> None:
    response = client.get(
        "/api/v1/metrics/security",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "timestamp" in body
    assert "authorization_denials_total" in body
    assert "hitl_events_total" in body
    assert "policy_decisions_total" in body
    assert "execution_tokens_issued" in body
    assert "execution_tokens_consumed" in body
    assert "execution_tokens_replayed" in body


@pytest.mark.asyncio
async def test_metrics_security_endpoint_requires_admin(
    client: TestClient, viewer_token: str,
) -> None:
    response = client.get(
        "/api/v1/metrics/security",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_metrics_security_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/metrics/security")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_compliance_evidence_endpoint_returns_package(
    client: TestClient, admin_token: str,
) -> None:
    response = client.get(
        "/api/v1/compliance/evidence",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "package_id" in body
    assert "generated_at" in body
    assert "access_control_evidence" in body
    assert "policy_evidence" in body
    assert "hitl_evidence" in body
    assert "authorization_evidence" in body
    assert "integrity" in body
    assert "Content-Disposition" in response.headers
    assert response.headers["Content-Disposition"].startswith("attachment;")


@pytest.mark.asyncio
async def test_compliance_evidence_endpoint_requires_admin(
    client: TestClient, viewer_token: str,
) -> None:
    response = client.get(
        "/api/v1/compliance/evidence",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_compliance_evidence_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/compliance/evidence")
    assert response.status_code == 401
