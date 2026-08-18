import pytest
from fastapi.testclient import TestClient

from app.domain.entities.user import User
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models.approval_request_model import ApprovalRequestModel
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService


async def _create_user_with_role(*, email: str, role: str) -> str:
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
async def admin_token(client: TestClient) -> str:
    return await _create_user_with_role(email="admin@example.com", role="admin")


@pytest.fixture
async def operator_token(client: TestClient) -> str:
    return await _create_user_with_role(email="operator@example.com", role="operator")


@pytest.fixture
async def viewer_token(client: TestClient) -> str:
    return await _create_user_with_role(email="viewer@example.com", role="viewer")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_authorized_approver_can_approve(client: TestClient, operator_token: str) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(intent_text="transfer $500", risk_score=0.85)

    response = client.post(
        f"/api/v1/approval/{request_id}/approve",
        headers=_auth_headers(operator_token),
    )
    assert response.status_code == 200
    assert response.json() == {"request_id": request_id, "status": "approved"}


@pytest.mark.asyncio
async def test_authorized_approver_can_reject(client: TestClient, operator_token: str) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(intent_text="delete table", risk_score=0.95)

    response = client.post(
        f"/api/v1/approval/{request_id}/reject",
        headers=_auth_headers(operator_token),
    )
    assert response.status_code == 200
    assert response.json() == {"request_id": request_id, "status": "rejected"}


@pytest.mark.asyncio
async def test_admin_can_approve(client: TestClient, admin_token: str) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(intent_text="transfer $500", risk_score=0.85)

    response = client.post(
        f"/api/v1/approval/{request_id}/approve",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_approve(client: TestClient, viewer_token: str) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(intent_text="transfer $500", risk_score=0.85)

    response = client.post(
        f"/api/v1/approval/{request_id}/approve",
        headers=_auth_headers(viewer_token),
    )
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_reject(client: TestClient, viewer_token: str) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(intent_text="delete table", risk_score=0.95)

    response = client.post(
        f"/api/v1/approval/{request_id}/reject",
        headers=_auth_headers(viewer_token),
    )
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


def test_unauthenticated_request_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/approval/req-123/approve")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_missing_role_is_rejected(client: TestClient) -> None:
    settings = get_settings()
    session = SessionLocal()
    try:
        repo = SQLAlchemyUserRepository(session)
        user = User(
            id=__import__("uuid").uuid4(),
            email="norole@example.com",
            hashed_password=BcryptPasswordHasher(rounds=4).hash("Password123!"),
            is_active=True,
            created_at=__import__("datetime").datetime.now(tz=__import__("datetime").UTC),
            role="",
        )
        saved = await repo.save(user)
        token = JWTTokenService(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_access_token_expire_minutes,
            clock_skew_seconds=settings.jwt_clock_skew_seconds,
        ).create_access_token(user_id=saved.id, email=saved.email)
        session.commit()
        response = client.post(
            "/api/v1/approval/req-123/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        session.close()


@pytest.mark.asyncio
async def test_privilege_escalation_attempt_fails(client: TestClient, viewer_token: str) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(intent_text="transfer $500", risk_score=0.85)

    response = client.post(
        f"/api/v1/approval/{request_id}/approve",
        headers=_auth_headers(viewer_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_approval_cannot_be_bypassed_through_alternate_path(
    client: TestClient, viewer_token: str
) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(
        intent_text="transfer $500", risk_score=0.85
    )

    response = client.post(
        f"/api/v1/approval/{request_id}/approve",
        headers=_auth_headers(viewer_token),
    )
    assert response.status_code == 403

    pending = await _hitl_queue.list_pending_requests()
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_rejection_cannot_be_bypassed_through_alternate_path(
    client: TestClient, viewer_token: str
) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(
        intent_text="delete table", risk_score=0.95
    )

    response = client.post(
        f"/api/v1/approval/{request_id}/reject",
        headers=_auth_headers(viewer_token),
    )
    assert response.status_code == 403

    pending = await _hitl_queue.list_pending_requests()
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_existing_hitl_behavior_still_works(
    client: TestClient, operator_token: str
) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    req_id1 = await _hitl_queue.enqueue_request(
        intent_text="transfer $500", risk_score=0.85
    )
    req_id2 = await _hitl_queue.enqueue_request(
        intent_text="delete table", risk_score=0.95
    )

    resp_pending = client.get(
        "/api/v1/approval/pending", headers=_auth_headers(operator_token)
    )
    assert resp_pending.status_code == 200
    assert len(resp_pending.json()["pending"]) == 2

    resp_approve = client.post(
        f"/api/v1/approval/{req_id1}/approve",
        headers=_auth_headers(operator_token),
    )
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "approved"

    resp_reject = client.post(
        f"/api/v1/approval/{req_id2}/reject",
        headers=_auth_headers(operator_token),
    )
    assert resp_reject.status_code == 200
    assert resp_reject.json()["status"] == "rejected"

    resp_pending_after = client.get(
        "/api/v1/approval/pending", headers=_auth_headers(operator_token)
    )
    assert resp_pending_after.status_code == 200
    assert len(resp_pending_after.json()["pending"]) == 0

    _hitl_queue.reset()


@pytest.mark.asyncio
async def test_database_state_remains_correct_after_authorization_failure(
    client: TestClient, viewer_token: str
) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(intent_text="transfer $500", risk_score=0.85)

    client.post(
        f"/api/v1/approval/{request_id}/approve",
        headers=_auth_headers(viewer_token),
    )

    with SessionLocal() as session:
        model = session.scalar(
            __import__("sqlalchemy").select(ApprovalRequestModel).where(
                ApprovalRequestModel.request_id == request_id
            )
        )
        assert model is not None
        assert model.status == "pending"
        assert model.decided_by is None
        assert model.decided_at is None


@pytest.mark.asyncio
async def test_authorization_failure_does_not_partially_mutate_approval_state(
    client: TestClient, viewer_token: str
) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    request_id = await _hitl_queue.enqueue_request(intent_text="delete table", risk_score=0.95)

    client.post(
        f"/api/v1/approval/{request_id}/reject",
        headers=_auth_headers(viewer_token),
    )

    with SessionLocal() as session:
        model = session.scalar(
            __import__("sqlalchemy").select(ApprovalRequestModel).where(
                ApprovalRequestModel.request_id == request_id
            )
        )
        assert model is not None
        assert model.status == "pending"
        assert model.decided_at is None
        assert model.decided_by is None


@pytest.mark.asyncio
async def test_authorized_approver_can_list_pending(
    client: TestClient, operator_token: str
) -> None:
    from app.presentation.api.v1.routes.approval import _hitl_queue

    _hitl_queue.reset()
    await _hitl_queue.enqueue_request(intent_text="transfer $500", risk_score=0.85)
    await _hitl_queue.enqueue_request(intent_text="delete table", risk_score=0.95)

    response = client.get(
        "/api/v1/approval/pending", headers=_auth_headers(operator_token)
    )
    assert response.status_code == 200
    assert len(response.json()["pending"]) == 2


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_list_pending(client: TestClient) -> None:
    response = client.get("/api/v1/approval/pending")
    assert response.status_code == 401
