from fastapi.testclient import TestClient


def test_execute_endpoint_rejects_replay(client: TestClient) -> None:
    """A token used once must be rejected on second use."""
    verify_response = client.post(
        "/api/v1/intent/verify",
        json={
            "user_prompt": "Transfer up to $100 to vendor account",
            "agent_id": "agent-123",
            "reasoning_step": "Decide payment",
            "proposed_tool": "transfer_funds",
            "tool_arguments": {"amount": 50, "recipient": "vendor-abc"},
        },
    )
    assert verify_response.status_code == 200
    token = verify_response.json()["ephemeral_token"]
    assert token

    # First execution should succeed
    execute_response = client.post(
        "/api/v1/intent/execute",
        json={"execution_token": token},
    )
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == "executed"

    # Replay must be rejected
    replay_response = client.post(
        "/api/v1/intent/execute",
        json={"execution_token": token},
    )
    assert replay_response.status_code == 401


def test_execute_endpoint_rejects_invalid_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intent/execute",
        json={"execution_token": "invalid-token"},
    )
    assert response.status_code == 401


def test_jwks_endpoint_returns_public_key(client: TestClient) -> None:
    response = client.get("/api/v1/.well-known/jwks.json")
    assert response.status_code == 200
    body = response.json()
    assert "keys" in body
    assert len(body["keys"]) == 1
    assert body["keys"][0]["kty"] == "OKP"


def test_readiness_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "not_ready"}
    assert body["db"] in {"ok", "unhealthy"}
