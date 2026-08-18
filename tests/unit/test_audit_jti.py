"""Tests for audit JTI logging."""

import json

from app.infrastructure.logging.audit_logger import LOG_PATH, log_verification


def test_log_verification_includes_jti() -> None:
    log_verification(
        agent_id="agent-1",
        proposed_tool="search",
        tool_arguments={"q": "test"},
        verification_status="PERMITTED",
        rejection_reason="",
        correlation_id="corr-123",
        jti="token-jti-456",
    )

    lines = [
        line for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    records = [json.loads(line) for line in lines]
    record = next(r for r in records if r.get("correlation_id") == "corr-123")
    assert record["event_type"] == "intent_verification"
    assert record["jti"] == "token-jti-456"
    assert record["correlation_id"] == "corr-123"
    assert record["verification_status"] == "PERMITTED"


def test_log_verification_without_jti() -> None:
    log_verification(
        agent_id="agent-1",
        proposed_tool="search",
        tool_arguments={"q": "test"},
        verification_status="BLOCKED",
        rejection_reason="Policy violation",
    )

    lines = [
        line for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    records = [json.loads(line) for line in lines]
    record = next(r for r in records if r.get("verification_status") == "BLOCKED")
    assert record["jti"] == ""
    assert record["verification_status"] == "BLOCKED"
