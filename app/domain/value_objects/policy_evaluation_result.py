from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.authorization_decision import AuthorizationDecision


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Result of evaluating a policy against an authorization context."""

    effect: AuthorizationDecision
    rule_id: str | None
    rule_version: str | None
    reason: str
