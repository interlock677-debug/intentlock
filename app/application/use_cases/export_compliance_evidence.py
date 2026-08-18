import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any


class ExportComplianceEvidenceUseCase:
    """Use case for generating tamper-evident compliance evidence packages."""

    def __init__(self, secret_key: str) -> None:
        if not secret_key:
            raise ValueError(
                "compliance_secret_key must be configured for compliance evidence exports."
            )
        self._secret_key = secret_key

    def execute(self) -> dict[str, Any]:
        """Generate a complete compliance evidence package.

        Includes access-control/RBAC evidence, policy version/history,
        HITL approval history, authorization decision logs, and integrity proof.
        """
        from app.domain.services.central_policy_engine import CentralPolicyEngine
        from app.infrastructure.logging.audit_logger import LOG_PATH

        policy_engine = CentralPolicyEngine.from_file()
        active_version = policy_engine.active_version()
        policy_set = policy_engine._store.get_active()

        policy_evidence: list[dict[str, Any]] = []
        if policy_set:
            for rule in policy_set.rules:
                policy_evidence.append({
                    "rule_id": rule.id,
                    "version": rule.version,
                    "effect": rule.effect,
                    "description": rule.description,
                    "priority": rule.priority,
                    "match": {
                        "tool": rule.match.tool,
                        "action": rule.match.action,
                        "resource": rule.match.resource,
                        "agent_id": rule.match.agent_id,
                        "user_id": rule.match.user_id,
                        "tenant_id": rule.match.tenant_id,
                        "service_id": rule.match.service_id,
                    },
                    "conditions": {
                        "min_confidence": (
                            rule.conditions.min_confidence if rule.conditions else None
                        ),
                        "max_risk_score": (
                            rule.conditions.max_risk_score if rule.conditions else None
                        ),
                    },
                })

        audit_records: list[dict[str, Any]] = []
        if LOG_PATH.exists():
            with LOG_PATH.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        audit_records.append(json.loads(line))

        authorization_logs: list[dict[str, Any]] = []
        hitl_history: list[dict[str, Any]] = []
        rbac_evidence: list[dict[str, Any]] = []

        for record in audit_records:
            event_type = record.get("event_type", "")
            if event_type == "intent_verification":
                authorization_logs.append({
                    "timestamp": record.get("timestamp"),
                    "correlation_id": record.get("correlation_id"),
                    "agent_id": record.get("agent_id"),
                    "proposed_tool": record.get("proposed_tool"),
                    "verification_status": record.get("verification_status"),
                    "rejection_reason": record.get("rejection_reason"),
                })
            elif event_type in ("approval_approved", "approval_rejected", "approval_expired"):
                hitl_history.append({
                    "timestamp": record.get("timestamp"),
                    "event_type": event_type,
                    "correlation_id": record.get("correlation_id"),
                    "request_id": record.get("request_id"),
                    "user_id": record.get("user_id"),
                    "risk_score": record.get("risk_score"),
                })
            elif event_type in ("user_registered", "user_activated", "user_deactivated"):
                rbac_evidence.append({
                    "timestamp": record.get("timestamp"),
                    "event_type": event_type,
                    "user_id": record.get("user_id"),
                    "email": record.get("email"),
                    "role": record.get("role"),
                })

        evidence_package = {
            "package_id": "",
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "schema_version": "1.0",
            "access_control_evidence": {
                "rbac_events": rbac_evidence,
                "total_rbac_events": len(rbac_evidence),
            },
            "policy_evidence": {
                "active_version": active_version,
                "default_effect": policy_set.default_effect if policy_set else "allow",
                "rules": policy_evidence,
                "total_rules": len(policy_evidence),
            },
            "hitl_evidence": {
                "events": hitl_history,
                "total_events": len(hitl_history),
            },
            "authorization_evidence": {
                "decision_logs": authorization_logs,
                "total_decisions": len(authorization_logs),
            },
        }
        evidence_package["package_id"] = self._generate_package_id(evidence_package)

        evidence_package["integrity"] = {
            "algorithm": "sha256",
            "hash": self._compute_package_hash(evidence_package),
            "signed_by": "intentlock-compliance",
        }

        return evidence_package

    def _generate_package_id(self, evidence_package: dict[str, Any]) -> str:
        content_hash = self._compute_package_hash(evidence_package)
        return hashlib.sha256(f"intentlock-compliance-{content_hash}".encode()).hexdigest()[:16]

    def _compute_package_hash(self, package: dict[str, Any]) -> str:
        stable_payload = {
            k: v
            for k, v in package.items()
            if k not in {"package_id", "generated_at"}
        }
        payload = json.dumps(stable_payload, sort_keys=True, default=str)
        return hmac.new(
            self._secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
