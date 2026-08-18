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


@pytest.fixture
async def auth_headers(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    session = SessionLocal()
    try:
        repo = SQLAlchemyUserRepository(session)
        user = User(
            id=__import__("uuid").uuid4(),
            email="approver@example.com",
            hashed_password=BcryptPasswordHasher(rounds=4).hash("Password123!"),
            is_active=True,
            created_at=__import__("datetime").datetime.now(tz=__import__("datetime").UTC),
            role="operator",
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
        return {"Authorization": f"Bearer {token}"}
    finally:
        session.close()


def test_list_pending_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/approval/pending")
    assert response.status_code == 401


def test_approve_unauthorized(client: TestClient) -> None:
    response = client.post("/api/v1/approval/req-123/approve")
    assert response.status_code == 401


def test_reject_unauthorized(client: TestClient) -> None:
    response = client.post("/api/v1/approval/req-123/reject")
    assert response.status_code == 401


def test_list_pending_empty(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/approval/pending", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"pending": []}


def test_approve_nonexistent_request(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/approval/nonexistent-id/approve", headers=auth_headers)
    assert response.status_code == 404
    assert "detail" in response.json()


def test_reject_nonexistent_request(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/approval/nonexistent-id/reject", headers=auth_headers)
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_approve_and_reject_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    req_id1 = await _hitl_queue.enqueue_request(intent_text="transfer $500", risk_score=0.85)
    req_id2 = await _hitl_queue.enqueue_request(intent_text="delete table", risk_score=0.95)

    # Check pending list
    resp_pending = client.get("/api/v1/approval/pending", headers=auth_headers)
    assert resp_pending.status_code == 200
    pending_list = resp_pending.json()["pending"]
    assert len(pending_list) == 2

    # Approve req_id1
    resp_approve = client.post(f"/api/v1/approval/{req_id1}/approve", headers=auth_headers)
    assert resp_approve.status_code == 200
    assert resp_approve.json() == {"request_id": req_id1, "status": "approved"}

    # Attempt to approve req_id1 again (fails)
    resp_approve_again = client.post(f"/api/v1/approval/{req_id1}/approve", headers=auth_headers)
    assert resp_approve_again.status_code == 404

    # Reject req_id2
    resp_reject = client.post(f"/api/v1/approval/{req_id2}/reject", headers=auth_headers)
    assert resp_reject.status_code == 200
    assert resp_reject.json() == {"request_id": req_id2, "status": "rejected"}

    # Attempt to reject req_id2 again (fails)
    resp_reject_again = client.post(f"/api/v1/approval/{req_id2}/reject", headers=auth_headers)
    assert resp_reject_again.status_code == 404

    _hitl_queue.reset()
