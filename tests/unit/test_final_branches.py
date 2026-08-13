from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.domain.models.intent import AgentActionDAG
from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.domain.services.policy_engine import PolicyEngine
from app.infrastructure.config.settings import Settings

# ---------- intent_evaluator 84->91: parsed but non-destructive ----------

def test_intent_evaluator_parsed_sql_type_not_in_destructive_set() -> None:
    """sqlglot parses; sql_type (SELECT) is not in destructive set -> None."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="Query",
        reasoning_step="Run",
        proposed_tool="sql_query",
        tool_arguments={"query": "SELECT * FROM users"},
    )
    assert evaluator._inspect_destructive_sql(intent) is None


# ---------- intent_evaluator 132-134: transfer amount from $ string on non-amount key ----------

def test_intent_evaluator_transfer_amount_from_dollar_string_other_key() -> None:
    """_extract_transfer_amount: a $ value in a non-amount key string."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="Send payment up to $500",
        reasoning_step="Send",
        proposed_tool="transfer_funds",
        tool_arguments={"note": "the cost is $400"},
    )
    # amount found via $ string in the note value: 400 < 500 -> valid.
    result = evaluator.evaluate(intent)
    assert result.is_valid


def test_intent_evaluator_transfer_amount_from_dollar_string_over_limit() -> None:
    """Amount from $ string in a non-amount key that exceeds the limit."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="Send payment up to $100",
        reasoning_step="Send",
        proposed_tool="transfer_funds",
        tool_arguments={"note": "the cost is $400"},
    )
    result = evaluator.evaluate(intent)
    assert not result.is_valid
    assert "exceeds the prompt limit" in result.reason


# ---------- intent_evaluator 178: ast.parse raises -> return False ----------

def test_intent_evaluator_ast_parse_fails_returns_false() -> None:
    """_contains_polyglot_payload: sqlglot raises, then ast.parse raises -> False."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="&&& this is not valid python or sql &&&",
        reasoning_step="step",
        proposed_tool="bash",
        tool_arguments={},
    )
    # sqlglot fails and ast.parse fails -> False.
    assert evaluator._contains_polyglot_payload(intent) is False


# ---------- policy_engine 119->108: simple yaml value without colon ----------

def test_policy_engine_simple_yaml_ignores_comment_and_blank() -> None:
    """_parse_simple_yaml skips comment and blank lines (loop-back branch)."""
    tmp = Path("tmp_policy.yaml")
    try:
        tmp.write_text(
            "# comment\n"
            "\n"
            "score_threshold: 0.5\n",
            encoding="utf-8",
        )
        with patch("app.domain.services.policy_engine.yaml", None):
            payload = PolicyEngine._parse_simple_yaml(tmp)
        assert payload["score_threshold"] == "0.5"
    finally:
        tmp.unlink(missing_ok=True)


def test_policy_engine_simple_yaml_handles_key_value_with_quotes() -> None:
    """_parse_simple_yaml strips quotes from values."""
    tmp = Path("tmp_policy2.yaml")
    try:
        tmp.write_text('name: "quoted"\n', encoding="utf-8")
        with patch("app.domain.services.policy_engine.yaml", None):
            payload = PolicyEngine._parse_simple_yaml(tmp)
        assert payload["name"] == "quoted"
    finally:
        tmp.unlink(missing_ok=True)


# ---------- settings 61, 70-71 ----------

def test_settings_cors_origins_plain_comma_string() -> None:
    """The field_validator parses a comma-separated string (line 61)."""
    # pydantic-settings JSON-decodes complex types, so the str branch is
    # exercised by invoking the validator directly with a str value.
    result = Settings.parse_cors_origins("http://a.com,http://b.com")
    assert result == ["http://a.com", "http://b.com"]


def test_settings_cors_origins_list_input() -> None:
    """The field_validator handles a list input (line 62)."""
    settings = Settings(cors_origins=["https://x.com"], _env_file=None)
    assert settings.cors_origins == ["https://x.com"]


def test_settings_rejects_placeholder_secret_prefix() -> None:
    """reject_placeholder_secret raises for 'change-me...' (line 70-71)."""
    with pytest.raises(ValueError) as exc:
        Settings(jwt_secret_key="change-me-123456789012345678901234567890", _env_file=None)
    assert "JWT_SECRET_KEY" in str(exc.value)


# ---------- audit_logger 14->20: handlers already present ----------

def test_audit_logger_module_handlers_already_present() -> None:
    """The module-level 'if not logger.handlers' is skipped when present."""
    import logging

    from app.infrastructure.logging import audit_logger

    # Verify the logger already has a handler (module init ran successfully).
    assert isinstance(audit_logger.logger, logging.Logger)
    assert audit_logger.logger.handlers


# ---------- langchain_adapter 29->31: name is not a str ----------

def test_langchain_adapter_name_attribute_not_string() -> None:
    """_resolve_tool_name: hasattr name but it's not a str -> fall through."""
    from sdk.langchain_adapter import IntentLockLangChainTool

    class ToolWithNonStrName:
        name = 123  # not a string

        def __call__(self) -> str:
            return "x"

    tool = IntentLockLangChainTool(ToolWithNonStrName())
    # Falls back to __class__.__name__.
    assert tool.tool_name == "ToolWithNonStrName"


# ---------- intent_evaluator 178: ast succeeds, sqlglot fails -> return True ----------

def test_intent_evaluator_ast_parse_succeeds_returns_true() -> None:
    """_contains_polyglot_payload: sqlglot fails, ast.parse succeeds -> True."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="def foo():\n    return 1",
        reasoning_step="",
        proposed_tool="bash",
        tool_arguments={},
    )
    # ast.parse succeeds on the python definition -> True.
    assert evaluator._contains_polyglot_payload(intent) is True


# ---------- policy_engine 119->108: line without colon ----------

def test_policy_engine_simple_yaml_skips_line_without_colon() -> None:
    """_parse_simple_yaml loops back for a line without a colon."""
    tmp = Path("tmp_policy3.yaml")
    try:
        tmp.write_text(
            "score_threshold: 0.5\n"
            "  - item without colon handling\n",
            encoding="utf-8",
        )
        with patch("app.domain.services.policy_engine.yaml", None):
            payload = PolicyEngine._parse_simple_yaml(tmp)
        assert payload["score_threshold"] == "0.5"
    finally:
        tmp.unlink(missing_ok=True)


# ---------- langchain_adapter 29->31: call with no positional args ----------

def test_langchain_adapter_call_no_positional_args() -> None:
    """__call__ with only kwargs -> the 'if args:' branch is skipped."""
    from unittest.mock import Mock, patch

    from sdk.langchain_adapter import IntentLockLangChainTool

    inner = Mock(return_value="done")
    inner.__name__ = "kw_only_tool"
    tool = IntentLockLangChainTool(inner)
    with patch("sdk.langchain_adapter.urlopen", return_value=type("R", (), {
        "getcode": lambda self: 200,
        "read": lambda self: b"{}",
        "__enter__": lambda self: self,
        "__exit__": lambda self, *a: None,
    })()):
        result = tool(my_kwarg=123, user_prompt="p", agent_id="a")
    assert result == "done"
    inner.assert_called_once_with(my_kwarg=123, user_prompt="p", agent_id="a")


# ---------- audit_logger 14->20: module reload with existing handlers ----------

def test_audit_logger_reload_skips_handler_creation() -> None:
    """Reloading the audit_logger module keeps existing handlers (branch 14->20)."""
    import importlib
    import logging

    import app.infrastructure.logging.audit_logger as audit_logger

    # Ensure the logger has handlers from the initial import.
    audit_logger.logger.handlers = []
    audit_logger.logger.addHandler(logging.NullHandler())
    importlib.reload(audit_logger)
    assert audit_logger.logger.handlers
