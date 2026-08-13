import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    # Register and login to get valid bearer token
    reg_payload = {
        "email": "approver@example.com",
        "password": "Password123!",
        "full_name": "Approver User",
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "approver@example.com", "password": "Password123!"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
