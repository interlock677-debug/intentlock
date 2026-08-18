import uuid
from pathlib import Path

import pytest

from app.domain.services.central_policy_engine import CentralPolicyEngine
from app.domain.services.policy_store import PolicyStore
from app.domain.value_objects.authorization_context import AuthorizationContext
from app.domain.value_objects.authorization_decision import AuthorizationDecision


def _make_context(**overrides: object) -> AuthorizationContext:
    defaults = {
        "user_id": uuid.UUID("12345678-1234-5678-1234-567812345678"),
        "agent_id": "agent-1",
        "proposed_tool": "search",
        "tenant_id": None,
        "action": "execute",
        "resource": "",
        "service_id": None,
    }
    defaults.update(overrides)
    return AuthorizationContext(**defaults)


class TestPolicyStore:
    def test_load_valid_policy(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "rule-1",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny dangerous tools",
                    "match": {"tool": "execute_sql"},
                    "priority": 100,
                }
            ],
        })
        assert store.get_active() is not None
        assert store.get_active().version == "1"
        assert len(store.get_active().rules) == 1

    def test_load_invalid_default_effect_raises(self) -> None:
        store = PolicyStore()
        with pytest.raises(ValueError, match="Invalid default_effect"):
            store.load("1", {"policy_version": "1", "default_effect": "invalid", "rules": []})

    def test_load_invalid_rule_effect_raises(self) -> None:
        store = PolicyStore()
        with pytest.raises(ValueError, match="Invalid effect"):
            store.load("1", {
                "policy_version": "1",
                "default_effect": "allow",
                "rules": [
                    {
                        "id": "r1",
                        "version": "1",
                        "effect": "invalid",
                        "description": "",
                        "match": {},
                    }
                ],
            })

    def test_load_rule_missing_id_raises(self) -> None:
        store = PolicyStore()
        with pytest.raises(ValueError, match="Rule missing id"):
            store.load("1", {
                "policy_version": "1",
                "default_effect": "allow",
                "rules": [{"version": "1", "effect": "deny", "description": "", "match": {}}],
            })

    def test_rollback_to_existing_version(self) -> None:
        store = PolicyStore()
        store.load("v1", {"policy_version": "v1", "default_effect": "allow", "rules": []})
        store.load("v2", {"policy_version": "v2", "default_effect": "deny", "rules": []})
        store.rollback("v1")
        assert store.active_version == "v1"
        assert store.get_active().default_effect == "allow"

    def test_rollback_to_unknown_version_raises(self) -> None:
        store = PolicyStore()
        with pytest.raises(ValueError, match="Unknown policy version"):
            store.rollback("unknown")

    def test_get_version_returns_none_for_missing(self) -> None:
        store = PolicyStore()
        assert store.get_version("missing") is None


class TestCentralPolicyEngine:
    def test_allow_when_no_active_policy(self) -> None:
        engine = CentralPolicyEngine(PolicyStore())
        result = engine.evaluate(_make_context())
        assert result.effect == AuthorizationDecision.ALLOW
        assert result.rule_id is None

    def test_deny_matching_rule(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-sql",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny SQL tools",
                    "match": {"tool": "execute_sql"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(proposed_tool="execute_sql"))
        assert result.effect == AuthorizationDecision.DENY
        assert result.rule_id == "deny-sql"

    def test_allow_non_matching_tool(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-sql",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny SQL tools",
                    "match": {"tool": "execute_sql"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(proposed_tool="search"))
        assert result.effect == AuthorizationDecision.ALLOW
        assert result.rule_id is None

    def test_conflicting_rules_higher_priority_wins(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "allow-search",
                    "version": "1",
                    "effect": "allow",
                    "description": "Allow search",
                    "match": {"tool": "search"},
                    "priority": 10,
                },
                {
                    "id": "deny-search",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny search",
                    "match": {"tool": "search"},
                    "priority": 100,
                },
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(proposed_tool="search"))
        assert result.effect == AuthorizationDecision.DENY
        assert result.rule_id == "deny-search"

    def test_precedence_by_priority(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "allow-low",
                    "version": "1",
                    "effect": "allow",
                    "description": "Low priority allow",
                    "match": {"tool": "search"},
                    "priority": 1,
                },
                {
                    "id": "deny-high",
                    "version": "1",
                    "effect": "deny",
                    "description": "High priority deny",
                    "match": {"tool": "search"},
                    "priority": 99,
                },
                {
                    "id": "hitl-medium",
                    "version": "1",
                    "effect": "require_hitl",
                    "description": "Medium priority HITL",
                    "match": {"tool": "search"},
                    "priority": 50,
                },
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(proposed_tool="search"))
        assert result.effect == AuthorizationDecision.DENY
        assert result.rule_id == "deny-high"

    def test_policy_version_selection(self) -> None:
        store = PolicyStore()
        store.load("v1", {"policy_version": "v1", "default_effect": "allow", "rules": []})
        store.load("v2", {"policy_version": "v2", "default_effect": "deny", "rules": []})
        engine = CentralPolicyEngine(store)
        assert engine.active_version() == "v2"
        engine.rollback("v1")
        assert engine.active_version() == "v1"

    def test_invalid_policy_raises(self) -> None:
        store = PolicyStore()
        with pytest.raises(ValueError, match="Missing policy_version"):
            store.load("1", {"rules": []})

    def test_require_hitl_matching_rule(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "hitl-transfer",
                    "version": "1",
                    "effect": "require_hitl",
                    "description": "HITL for transfers",
                    "match": {"tool": "transfer_funds"},
                    "priority": 50,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(proposed_tool="transfer_funds"))
        assert result.effect == AuthorizationDecision.REQUIRE_HITL
        assert result.rule_id == "hitl-transfer"

    def test_match_on_multiple_tool_values(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-batch",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny batch tools",
                    "match": {"tool": ["batch_delete", "batch_update"]},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(proposed_tool="batch_delete"))
        assert result.effect == AuthorizationDecision.DENY
        result = engine.evaluate(_make_context(proposed_tool="batch_update"))
        assert result.effect == AuthorizationDecision.DENY
        result = engine.evaluate(_make_context(proposed_tool="search"))
        assert result.effect == AuthorizationDecision.ALLOW

    def test_match_on_tenant(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-tenant",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny for tenant",
                    "match": {"tenant_id": "blocked-tenant"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(tenant_id="blocked-tenant"))
        assert result.effect == AuthorizationDecision.DENY
        result = engine.evaluate(_make_context(tenant_id="safe-tenant"))
        assert result.effect == AuthorizationDecision.ALLOW

    def test_match_on_action(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-delete",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny delete actions",
                    "match": {"action": "delete"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(action="delete"))
        assert result.effect == AuthorizationDecision.DENY
        result = engine.evaluate(_make_context(action="read"))
        assert result.effect == AuthorizationDecision.ALLOW

    def test_match_on_resource(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-resource",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny resource",
                    "match": {"resource": "sensitive-data"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(resource="sensitive-data"))
        assert result.effect == AuthorizationDecision.DENY
        result = engine.evaluate(_make_context(resource="public-data"))
        assert result.effect == AuthorizationDecision.ALLOW

    def test_match_on_agent_id(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-agent",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny agent",
                    "match": {"agent_id": "blocked-agent"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(agent_id="blocked-agent"))
        assert result.effect == AuthorizationDecision.DENY
        result = engine.evaluate(_make_context(agent_id="safe-agent"))
        assert result.effect == AuthorizationDecision.ALLOW

    def test_match_on_user_id(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-user",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny user",
                    "match": {"user_id": "12345678-1234-5678-1234-567812345678"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context())
        assert result.effect == AuthorizationDecision.DENY
        other_user = uuid.UUID("99999999-9999-9999-9999-999999999999")
        result = engine.evaluate(_make_context(user_id=other_user))
        assert result.effect == AuthorizationDecision.ALLOW

    def test_match_on_service_id(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-service",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny service",
                    "match": {"service_id": "blocked-service"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(service_id="blocked-service"))
        assert result.effect == AuthorizationDecision.DENY
        result = engine.evaluate(_make_context(service_id="safe-service"))
        assert result.effect == AuthorizationDecision.ALLOW

    def test_conditions_max_risk_score_filters_rule(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "hitl-low-risk",
                    "version": "1",
                    "effect": "require_hitl",
                    "description": "HITL for low risk only",
                    "match": {"tool": "search"},
                    "conditions": {"max_risk_score": 0.5},
                    "priority": 50,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(proposed_tool="search"), risk_score=0.3)
        assert result.effect == AuthorizationDecision.REQUIRE_HITL
        result = engine.evaluate(_make_context(proposed_tool="search"), risk_score=0.8)
        assert result.effect == AuthorizationDecision.ALLOW

    def test_conditions_min_confidence_filters_rule(self) -> None:
        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "hitl-low-conf",
                    "version": "1",
                    "effect": "require_hitl",
                    "description": "HITL for low confidence",
                    "match": {"tool": "search"},
                    "conditions": {"min_confidence": 0.9},
                    "priority": 50,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        result = engine.evaluate(_make_context(proposed_tool="search"), confidence=0.8)
        assert result.effect == AuthorizationDecision.ALLOW
        result = engine.evaluate(_make_context(proposed_tool="search"), confidence=0.95)
        assert result.effect == AuthorizationDecision.REQUIRE_HITL

    def test_load_rules_not_a_list_raises(self) -> None:
        store = PolicyStore()
        with pytest.raises(ValueError, match="rules must be a list"):
            store.load(
                "1",
                {
                    "policy_version": "1",
                    "default_effect": "allow",
                    "rules": "not-a-list",
                },
            )

    def test_coerce_string_or_list_with_number(self) -> None:
        result = PolicyStore._coerce_string_or_list(42)
        assert result == "42"

    def test_try_float_with_invalid_string(self) -> None:
        result = PolicyStore._try_float("not-a-number")
        assert result is None

    def test_policy_rollback_preserves_versions(self) -> None:
        store = PolicyStore()
        store.load("v1", {"policy_version": "v1", "default_effect": "allow", "rules": []})
        store.load("v2", {"policy_version": "v2", "default_effect": "deny", "rules": []})
        store.rollback("v1")
        assert store.active_version == "v1"
        assert store.get_version("v2") is not None

    def test_concurrent_evaluation_is_safe(self) -> None:
        import threading

        store = PolicyStore()
        store.load("1", {
            "policy_version": "1",
            "default_effect": "allow",
            "rules": [
                {
                    "id": "deny-tool",
                    "version": "1",
                    "effect": "deny",
                    "description": "Deny tool",
                    "match": {"tool": "blocked"},
                    "priority": 100,
                }
            ],
        })
        engine = CentralPolicyEngine(store)
        errors: list[Exception] = []

        def evaluate() -> None:
            try:
                for _ in range(100):
                    engine.evaluate(_make_context(proposed_tool="blocked"))
                    engine.evaluate(_make_context(proposed_tool="safe"))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=evaluate) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_from_file_loads_valid_policy(self) -> None:
        engine = CentralPolicyEngine.from_file(path="config/policies.yaml")
        result = engine.evaluate(_make_context(proposed_tool="execute_sql"))
        assert result.effect == AuthorizationDecision.DENY

    def test_from_file_missing_file_returns_empty_engine(self) -> None:
        engine = CentralPolicyEngine.from_file(path="/nonexistent/policies.yaml")
        result = engine.evaluate(_make_context())
        assert result.effect == AuthorizationDecision.ALLOW

    def test_from_file_non_dict_yaml_returns_empty_engine(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "policies.yaml"
        yaml_file.write_text("just a string\n", encoding="utf-8")
        engine = CentralPolicyEngine.from_file(path=str(yaml_file))
        result = engine.evaluate(_make_context())
        assert result.effect == AuthorizationDecision.ALLOW

    def test_load_non_dict_rule_raises(self) -> None:
        store = PolicyStore()
        with pytest.raises(ValueError, match="Invalid rule"):
            store.load(
                "1",
                {
                    "policy_version": "1",
                    "default_effect": "allow",
                    "rules": ["not-a-dict-rule"],
                },
            )

    def test_parse_rule_non_dict_match_coerces_to_empty(self) -> None:
        store = PolicyStore()
        store.load(
            "1",
            {
                "policy_version": "1",
                "default_effect": "allow",
                "rules": [
                    {
                        "id": "r1",
                        "version": "1",
                        "effect": "deny",
                        "description": "",
                        "match": "not-a-dict",
                    }
                ],
            },
        )
        assert store.get_active() is not None
        assert len(store.get_active().rules) == 1
        assert store.get_active().rules[0].match.tool is None

    def test_value_matches_none_actual_returns_false(self) -> None:
        assert CentralPolicyEngine._value_matches("expected", None) is False

    def test_value_matches_none_expected_returns_false(self) -> None:
        assert CentralPolicyEngine._value_matches(None, "actual") is False
