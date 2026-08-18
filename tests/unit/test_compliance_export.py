import json

import pytest

from app.application.use_cases.export_compliance_evidence import ExportComplianceEvidenceUseCase


@pytest.fixture(autouse=True)
def _clear_audit_log() -> None:
    from app.infrastructure.logging.audit_logger import LOG_PATH

    if LOG_PATH.exists():
        LOG_PATH.unlink()
    yield
    if LOG_PATH.exists():
        LOG_PATH.unlink()


def _write_compliance_record(event_type: str, **extra: object) -> None:
    from app.infrastructure.logging.audit_logger import log_compliance_event

    defaults = {
        "correlation_id": "corr-123",
        "agent_id": "agent-1",
        "user_id": "user-1",
        "email": "test@example.com",
        "role": "admin",
    }
    defaults.update(extra)
    log_compliance_event(event_type, **defaults)


def test_export_compliance_evidence_returns_package() -> None:
    _write_compliance_record(
        "intent_verification", proposed_tool="search", verification_status="PERMITTED"
    )
    _write_compliance_record("approval_approved", request_id="req-1", risk_score=0.5)

    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()

    assert "package_id" in evidence
    assert "generated_at" in evidence
    assert "access_control_evidence" in evidence
    assert "policy_evidence" in evidence
    assert "hitl_evidence" in evidence
    assert "authorization_evidence" in evidence
    assert "integrity" in evidence
    assert evidence["integrity"]["algorithm"] == "sha256"
    assert len(evidence["integrity"]["hash"]) == 64


def test_export_compliance_evidence_authorization_logs() -> None:
    _write_compliance_record(
        "intent_verification", proposed_tool="search", verification_status="PERMITTED"
    )
    _write_compliance_record(
        "intent_verification",
        proposed_tool="transfer",
        verification_status="AUTH_DENIED",
        rejection_reason="denied",
    )

    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()

    auth_evidence = evidence["authorization_evidence"]
    assert auth_evidence["total_decisions"] == 2
    assert len(auth_evidence["decision_logs"]) == 2
    assert auth_evidence["decision_logs"][0]["proposed_tool"] == "search"
    assert auth_evidence["decision_logs"][1]["rejection_reason"] == "denied"


def test_export_compliance_evidence_hitl_history() -> None:
    _write_compliance_record("approval_approved", request_id="req-1", risk_score=0.5)
    _write_compliance_record("approval_rejected", request_id="req-2", risk_score=0.8)

    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()

    hitl_evidence = evidence["hitl_evidence"]
    assert hitl_evidence["total_events"] == 2
    assert hitl_evidence["events"][0]["event_type"] == "approval_approved"
    assert hitl_evidence["events"][1]["event_type"] == "approval_rejected"


def test_export_compliance_evidence_empty_logs() -> None:
    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()

    assert evidence["authorization_evidence"]["total_decisions"] == 0
    assert evidence["hitl_evidence"]["total_events"] == 0
    assert evidence["access_control_evidence"]["total_rbac_events"] == 0


def test_export_compliance_evidence_package_id_is_deterministic() -> None:
    _write_compliance_record(
        "intent_verification", proposed_tool="search", verification_status="PERMITTED"
    )

    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence1 = use_case.execute()
    evidence2 = use_case.execute()

    assert evidence1["package_id"] == evidence2["package_id"]


def test_export_compliance_evidence_integrity_hash_changes_with_content() -> None:
    _write_compliance_record(
        "intent_verification", proposed_tool="search", verification_status="PERMITTED"
    )
    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence1 = use_case.execute()

    _write_compliance_record(
        "intent_verification", proposed_tool="delete", verification_status="AUTH_DENIED"
    )
    evidence2 = use_case.execute()

    assert evidence1["integrity"]["hash"] != evidence2["integrity"]["hash"]


def test_export_compliance_evidence_returns_json_serializable() -> None:
    _write_compliance_record(
        "intent_verification", proposed_tool="search", verification_status="PERMITTED"
    )
    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()

    serialized = json.dumps(evidence, default=str)
    assert isinstance(serialized, str)
    parsed = json.loads(serialized)
    assert parsed["package_id"] == evidence["package_id"]


def test_export_compliance_evidence_user_deactivated_event() -> None:
    _write_compliance_record("user_deactivated", user_id="user-1", role="admin")
    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()

    rbac = evidence["access_control_evidence"]
    assert rbac["total_rbac_events"] == 1
    assert rbac["rbac_events"][0]["event_type"] == "user_deactivated"


def test_export_compliance_evidence_empty_log_file_missing() -> None:
    from app.infrastructure.logging.audit_logger import LOG_PATH

    if LOG_PATH.exists():
        LOG_PATH.unlink()
    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()
    assert evidence["authorization_evidence"]["total_decisions"] == 0
    assert evidence["hitl_evidence"]["total_events"] == 0
    assert evidence["access_control_evidence"]["total_rbac_events"] == 0


def test_export_compliance_evidence_no_active_policy_set() -> None:
    from unittest.mock import patch

    mock_engine = type("MockEngine", (), {})()
    mock_engine.active_version = lambda: None
    mock_engine._store = type("MockStore", (), {})()
    mock_engine._store.get_active = lambda: None

    with patch(
        "app.domain.services.central_policy_engine.CentralPolicyEngine.from_file",
        return_value=mock_engine,
    ):
        use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
        evidence = use_case.execute()
        assert evidence["policy_evidence"]["active_version"] is None
        assert evidence["policy_evidence"]["default_effect"] == "allow"
        assert evidence["policy_evidence"]["total_rules"] == 0


def test_export_compliance_evidence_empty_line_in_audit_log() -> None:
    from app.infrastructure.logging.audit_logger import LOG_PATH

    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()
    assert evidence["authorization_evidence"]["total_decisions"] == 0
    assert evidence["hitl_evidence"]["total_events"] == 0


def test_export_compliance_evidence_unhandled_event_type() -> None:
    _write_compliance_record("unknown_event_type", foo="bar")
    use_case = ExportComplianceEvidenceUseCase(secret_key="test-secret-key")
    evidence = use_case.execute()
    assert evidence["authorization_evidence"]["total_decisions"] == 0
    assert evidence["hitl_evidence"]["total_events"] == 0
    assert evidence["access_control_evidence"]["total_rbac_events"] == 0


def test_export_compliance_evidence_requires_secret_key() -> None:
    with pytest.raises(ValueError, match="compliance_secret_key must be configured"):
        ExportComplianceEvidenceUseCase(secret_key="")


def test_export_compliance_evidence_integrity_with_different_secret() -> None:
    _write_compliance_record(
        "intent_verification", proposed_tool="search", verification_status="PERMITTED"
    )
    use_case_a = ExportComplianceEvidenceUseCase(secret_key="secret-a")
    use_case_b = ExportComplianceEvidenceUseCase(secret_key="secret-b")
    evidence_a = use_case_a.execute()
    evidence_b = use_case_b.execute()
    assert evidence_a["integrity"]["hash"] != evidence_b["integrity"]["hash"]
