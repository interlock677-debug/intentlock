import json
from pathlib import Path

from fastapi.testclient import TestClient

AUDIT_LOG_PATH = Path("logs") / "audit_trail.jsonl"


def test_intent_verification_audit_records_written(client: TestClient) -> None:
    if AUDIT_LOG_PATH.exists():
        AUDIT_LOG_PATH.unlink()

    response = client.post(
        "/api/v1/intent/verify",
        json={
            "user_prompt": "Transfer up to $100 to vendor account",
            "agent_id": "agent-123",
            "reasoning_step": "Decide payment",
            "proposed_tool": "transfer_funds",
            "tool_arguments": {"amount": 50, "recipient": "vendor-abc"},
        },
    )

    assert response.status_code == 200
    assert AUDIT_LOG_PATH.exists()

    with AUDIT_LOG_PATH.open("r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    assert len(lines) >= 1
    record = json.loads(lines[-1])
    assert record["agent_id"] == "agent-123"
    assert record["proposed_tool"] == "transfer_funds"
    assert record["verification_status"] == "PERMITTED"
    assert record["rejection_reason"] == ""
