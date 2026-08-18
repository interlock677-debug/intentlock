from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyMatch:
    """Match criteria for a policy rule."""

    tool: str | list[str] | None = None
    action: str | list[str] | None = None
    resource: str | list[str] | None = None
    agent_id: str | list[str] | None = None
    user_id: str | list[str] | None = None
    tenant_id: str | list[str] | None = None
    service_id: str | list[str] | None = None


@dataclass(frozen=True)
class PolicyConditions:
    """Additional conditions that must be met for a rule to apply."""

    min_confidence: float | None = None
    max_risk_score: float | None = None


@dataclass(frozen=True)
class PolicyRule:
    """A single versioned policy rule."""

    id: str
    version: str
    effect: str
    description: str
    match: PolicyMatch
    conditions: PolicyConditions | None = None
    priority: int = 0
