import json
from pathlib import Path

import pytest

from app.infrastructure.logging.audit_logger import (
    LOG_PATH,
    _compute_hash,
    _compute_hash_without_hash_fields,
    _get_last_hash,
    _verify_hash_chain,
    export_audit_log,
    get_audit_evidence,
    log_compliance_event,
    log_security_event,
    log_verification,
)


@pytest.fixture(autouse=True)
def _clear_audit_log() -> None:
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    yield
    if LOG_PATH.exists():
        LOG_PATH.unlink()


def test_log_verification_writes_record() -> None:
    log_verification(
        agent_id="agent-1",
        proposed_tool="search",
        tool_arguments={"query": "test"},
        verification_status="PERMITTED",
        correlation_id="corr-1",
    )
    assert LOG_PATH.exists()
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        record = json.loads(handle.readline())
    assert record["event_type"] == "intent_verification"
    assert record["agent_id"] == "agent-1"
    assert record["proposed_tool"] == "search"
    assert record["verification_status"] == "PERMITTED"
    assert record["correlation_id"] == "corr-1"
    assert record["jti"] == ""


def test_log_verification_with_jti() -> None:
    log_verification(
        agent_id="agent-1",
        proposed_tool="search",
        tool_arguments={"query": "test"},
        verification_status="PERMITTED",
        jti="token-jti-123",
    )
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        record = json.loads(handle.readline())
    assert record["jti"] == "token-jti-123"


def test_log_security_event_writes_record() -> None:
    log_security_event(
        "rate_limit_exceeded",
        correlation_id="corr-2",
        client_ip="10.0.0.1",
    )
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        record = json.loads(handle.readline())
    assert record["event_type"] == "rate_limit_exceeded"
    assert record["correlation_id"] == "corr-2"
    assert record["client_ip"] == "10.0.0.1"


def test_log_compliance_event_writes_hash_chain() -> None:
    log_compliance_event("user_registered", user_id="user-1", role="admin")
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        record = json.loads(handle.readline())
    assert record["event_type"] == "user_registered"
    assert "previous_hash" in record
    assert "hash" in record
    assert record["previous_hash"] == ""
    assert len(record["hash"]) == 64


def test_log_compliance_event_chain_links() -> None:
    log_compliance_event("event_a", key="a")
    log_compliance_event("event_b", key="b")
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["hash"] == second["previous_hash"]


def test_get_last_hash_empty_log() -> None:
    assert _get_last_hash() == ""


def test_get_last_hash_empty_file() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch()
    assert _get_last_hash() == ""


def test_get_last_hash_blank_last_line() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    assert _get_last_hash() == ""


def test_get_last_hash_with_chain() -> None:
    log_compliance_event("event_a")
    log_compliance_event("event_b")
    last_hash = _get_last_hash()
    assert len(last_hash) == 64


def test_get_last_hash_with_corrupted_record() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")
    assert _get_last_hash() == ""


def test_verify_hash_chain_empty_records() -> None:
    assert _verify_hash_chain([]) is True


def test_verify_hash_chain_valid() -> None:
    log_compliance_event("event_a")
    log_compliance_event("event_b")
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    assert _verify_hash_chain(records) is True


def test_verify_hash_chain_tampered_hash() -> None:
    log_compliance_event("event_a")
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    records[0]["hash"] = "tampered"
    assert _verify_hash_chain(records) is False


def test_verify_hash_chain_first_record_has_previous_hash() -> None:
    record = {"event_type": "x", "previous_hash": "abc", "hash": "def"}
    assert _verify_hash_chain([record]) is False


def test_verify_hash_chain_broken_chain() -> None:
    record_a = {"event_type": "a"}
    hash_a = _compute_hash_without_hash_fields(record_a)
    record_a["hash"] = hash_a
    record_a["previous_hash"] = ""

    record_b = {"event_type": "b"}
    hash_b = _compute_hash_without_hash_fields(record_b)
    record_b["hash"] = hash_b
    record_b["previous_hash"] = "wrong"

    assert _verify_hash_chain([record_a, record_b]) is False


def test_compute_hash_deterministic() -> None:
    record = {"event_type": "test", "key": "value"}
    assert _compute_hash(record) == _compute_hash(record)


def test_compute_hash_excludes_hash_fields() -> None:
    record = {"event_type": "test", "hash": "abc", "previous_hash": "def"}
    assert _compute_hash_without_hash_fields(record) == _compute_hash({"event_type": "test"})


def test_export_audit_log_writes_file(tmp_path: Path) -> None:
    output = tmp_path / "export.json"
    log_compliance_event("event_a")
    result = export_audit_log(str(output))
    assert output.exists()
    assert result["record_count"] == 1
    assert result["chain_valid"] is True


def test_export_audit_log_no_log_file(tmp_path: Path) -> None:
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    output = tmp_path / "export.json"
    result = export_audit_log(str(output))
    assert result["record_count"] == 0
    assert result["chain_valid"] is True


def test_export_audit_log_skips_blank_lines(tmp_path: Path) -> None:
    output = tmp_path / "export.json"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n")
        handle.write("\n")
    result = export_audit_log(str(output))
    assert result["record_count"] == 0
    assert result["chain_valid"] is True


def test_get_audit_evidence_empty() -> None:
    evidence = get_audit_evidence()
    assert evidence["record_count"] == 0
    assert evidence["chain_valid"] is True


def test_get_audit_evidence_with_time_filters() -> None:
    log_compliance_event("event_a")
    evidence = get_audit_evidence(
        since="2099-01-01T00:00:00+00:00",
        until="2099-12-31T23:59:59+00:00",
    )
    assert evidence["record_count"] == 0


def test_get_audit_evidence_in_time_range() -> None:
    log_compliance_event("event_a")
    evidence = get_audit_evidence(
        since="2000-01-01T00:00:00+00:00",
        until="2099-12-31T23:59:59+00:00",
    )
    assert evidence["record_count"] == 1


def test_get_audit_evidence_with_until_filter() -> None:
    log_compliance_event("event_a")
    evidence = get_audit_evidence(
        since="2000-01-01T00:00:00+00:00",
        until="2000-12-31T23:59:59+00:00",
    )
    assert evidence["record_count"] == 0


def test_get_audit_evidence_skips_blank_lines() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n")
        handle.write("\n")
    evidence = get_audit_evidence()
    assert evidence["record_count"] == 0
