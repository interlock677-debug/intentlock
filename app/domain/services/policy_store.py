from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.domain.value_objects.policy_rule import PolicyConditions, PolicyMatch, PolicyRule


@dataclass
class PolicySet:
    """A versioned collection of policy rules."""

    version: str
    default_effect: str = "allow"
    rules: list[PolicyRule] = field(default_factory=list)
    loaded_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class PolicyStore:
    """Stores and manages versioned policy sets with rollback support."""

    def __init__(self) -> None:
        self._versions: dict[str, PolicySet] = {}
        self._active_version: str | None = None

    def load(self, version: str, data: dict[str, Any]) -> None:
        if "policy_version" not in data:
            raise ValueError("Missing policy_version")

        default_effect = str(data.get("default_effect", "allow")).lower()
        if default_effect not in ("allow", "deny", "require_hitl"):
            raise ValueError(f"Invalid default_effect: {default_effect}")

        raw_rules = data.get("rules", [])
        if not isinstance(raw_rules, list):
            raise ValueError("rules must be a list")

        rules: list[PolicyRule] = []
        for raw in raw_rules:
            if not isinstance(raw, dict):
                raise ValueError(f"Invalid rule: {raw}")
            rule = self._parse_rule(raw)
            rules.append(rule)

        policy_set = PolicySet(
            version=version,
            default_effect=default_effect,
            rules=rules,
        )
        self._versions[version] = policy_set
        self._active_version = version

    @property
    def active_version(self) -> str | None:
        return self._active_version

    def activate(self, version: str) -> None:
        if version not in self._versions:
            raise ValueError(f"Unknown policy version: {version}")
        self._active_version = version

    def rollback(self, version: str) -> None:
        self.activate(version)

    def get_active(self) -> PolicySet | None:
        if self._active_version is None:
            return None
        return self._versions.get(self._active_version)

    def get_version(self, version: str) -> PolicySet | None:
        return self._versions.get(version)

    @staticmethod
    def _parse_rule(raw: dict[str, Any]) -> PolicyRule:
        rule_id = str(raw.get("id", ""))
        if not rule_id:
            raise ValueError("Rule missing id")
        version = str(raw.get("version", "1"))
        effect = str(raw.get("effect", "allow")).lower()
        if effect not in ("allow", "deny", "require_hitl"):
            raise ValueError(f"Invalid effect for rule {rule_id}: {effect}")
        description = str(raw.get("description", ""))
        priority = int(raw.get("priority", 0))

        match_data = raw.get("match", {})
        if not isinstance(match_data, dict):
            match_data = {}
        match = PolicyMatch(
            tool=PolicyStore._coerce_string_or_list(match_data.get("tool")),
            action=PolicyStore._coerce_string_or_list(match_data.get("action")),
            resource=PolicyStore._coerce_string_or_list(match_data.get("resource")),
            agent_id=PolicyStore._coerce_string_or_list(match_data.get("agent_id")),
            user_id=PolicyStore._coerce_string_or_list(match_data.get("user_id")),
            tenant_id=PolicyStore._coerce_string_or_list(match_data.get("tenant_id")),
            service_id=PolicyStore._coerce_string_or_list(match_data.get("service_id")),
        )

        conditions_data = raw.get("conditions")
        conditions = None
        if isinstance(conditions_data, dict):
            conditions = PolicyConditions(
                min_confidence=PolicyStore._try_float(conditions_data.get("min_confidence")),
                max_risk_score=PolicyStore._try_float(conditions_data.get("max_risk_score")),
            )

        return PolicyRule(
            id=rule_id,
            version=version,
            effect=effect,
            description=description,
            match=match,
            conditions=conditions,
            priority=priority,
        )

    @staticmethod
    def _coerce_string_or_list(value: Any) -> str | list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return [str(v) for v in value]
        return str(value)

    @staticmethod
    def _try_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
