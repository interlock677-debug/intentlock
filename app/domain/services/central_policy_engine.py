from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from app.domain.services.policy_store import PolicyStore
from app.domain.value_objects.authorization_context import AuthorizationContext
from app.domain.value_objects.authorization_decision import AuthorizationDecision
from app.domain.value_objects.policy_evaluation_result import PolicyEvaluationResult
from app.domain.value_objects.policy_rule import PolicyMatch


class CentralPolicyEngine:
    """Centralized policy engine with versioned rules, precedence, and conditions.

    Evaluates identity-based allow/deny/require_hitl rules in priority order.
    Policies are deterministic, auditable, and support safe rollback.
    """

    def __init__(self, store: PolicyStore | None = None) -> None:
        self._store = store or PolicyStore()

    def load_policy(self, data: dict[str, Any]) -> None:
        version = str(data.get("policy_version", "1"))
        self._store.load(version, data)

    def evaluate(
        self,
        context: AuthorizationContext,
        confidence: float = 1.0,
        risk_score: float = 0.0,
    ) -> PolicyEvaluationResult:
        policy = self._store.get_active()
        if policy is None:
            return PolicyEvaluationResult(
                effect=AuthorizationDecision.ALLOW,
                rule_id=None,
                rule_version=None,
                reason="No active policy; default allow",
            )

        matching_rules = [
            r for r in policy.rules if self._matches(r.match, context)
        ]

        applicable_rules = [
            r for r in matching_rules if self._conditions_met(r.conditions, confidence, risk_score)
        ]

        if not applicable_rules:
            default = AuthorizationDecision(policy.default_effect)
            return PolicyEvaluationResult(
                effect=default,
                rule_id=None,
                rule_version=policy.version,
                reason=f"Default policy ({policy.version})",
            )

        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        winner = applicable_rules[0]
        effect = AuthorizationDecision(winner.effect)

        return PolicyEvaluationResult(
            effect=effect,
            rule_id=winner.id,
            rule_version=winner.version,
            reason=winner.description or f"Matched rule {winner.id}",
        )

    def rollback(self, version: str) -> None:
        self._store.rollback(version)

    def active_version(self) -> str | None:
        return self._store._active_version

    @classmethod
    def from_file(cls, path: str | Path | None = None) -> CentralPolicyEngine:
        policy_path = Path(
            path or os.getenv("POLICY_FILE_PATH") or cls._default_policy_path(),
        )
        engine = cls()
        if policy_path.exists():
            with policy_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            if isinstance(data, dict) and ("policy_version" in data or "rules" in data):
                engine.load_policy(data)
        return engine

    @staticmethod
    def _default_policy_path() -> Path:
        return Path(__file__).resolve().parents[3] / "config" / "policies.yaml"

    @staticmethod
    def _matches(match: PolicyMatch, context: AuthorizationContext) -> bool:
        if match.tool is not None and not CentralPolicyEngine._value_matches(
            match.tool, context.proposed_tool
        ):
            return False
        if match.action is not None and not CentralPolicyEngine._value_matches(
            match.action, context.action
        ):
            return False
        if match.resource is not None and not CentralPolicyEngine._value_matches(
            match.resource, context.resource
        ):
            return False
        if match.agent_id is not None and not CentralPolicyEngine._value_matches(
            match.agent_id, context.agent_id
        ):
            return False
        if match.user_id is not None and not CentralPolicyEngine._value_matches(
            match.user_id, str(context.user_id)
        ):
            return False
        if match.tenant_id is not None and not CentralPolicyEngine._value_matches(
            match.tenant_id, context.tenant_id
        ):
            return False
        return not (
            match.service_id is not None
            and not CentralPolicyEngine._value_matches(
                match.service_id, context.service_id
            )
        )

    @staticmethod
    def _value_matches(
        expected: str | list[str] | None,
        actual: str | None,
    ) -> bool:
        if actual is None or expected is None:
            return False
        if isinstance(expected, str):
            return expected == actual
        return actual in expected

    @staticmethod
    def _conditions_met(
        conditions: Any, confidence: float, risk_score: float
    ) -> bool:
        if conditions is None:
            return True
        if conditions.min_confidence is not None and confidence < conditions.min_confidence:
            return False
        return not (
            conditions.max_risk_score is not None
            and risk_score > conditions.max_risk_score
        )
