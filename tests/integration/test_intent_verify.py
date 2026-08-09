from fastapi.testclient import TestClient


def test_intent_verify_returns_ephemeral_token(client: TestClient) -> None:
    payload = {
        "user_prompt": "Transfer up to $100 to vendor account",
        "agent_id": "agent-123",
        "reasoning_step": "Decide payment",
        "proposed_tool": "transfer_funds",
        "tool_arguments": {"amount": 50, "recipient": "vendor-abc"},
    }

    response = client.post("/api/v1/intent/verify", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["ephemeral_token"]
    assert body["confidence_score"] > 0.9


def test_intent_verify_rejects_destructive_sql(client: TestClient) -> None:
    payload = {
        "user_prompt": "Run a harmful query",
        "agent_id": "agent-123",
        "reasoning_step": "Cleanup database",
        "proposed_tool": "execute_sql",
        "tool_arguments": {"query": "DROP TABLE users;"},
    }

    response = client.post("/api/v1/intent/verify", json=payload)

    assert response.status_code == 403
    assert "Destructive SQL" in response.json()["detail"]


def test_intent_verify_rejects_overlimit_transfer(client: TestClient) -> None:
    payload = {
        "user_prompt": "Transfer no more than $100",
        "agent_id": "agent-123",
        "reasoning_step": "Send payment",
        "proposed_tool": "transfer_funds",
        "tool_arguments": {"amount": 150, "recipient": "vendor-abc"},
    }

    response = client.post("/api/v1/intent/verify", json=payload)

    assert response.status_code == 403
    assert "exceeds the prompt limit" in response.json()["detail"]
