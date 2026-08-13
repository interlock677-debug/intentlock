from __future__ import annotations

from unittest.mock import patch

from app.domain.models.intent import AgentActionDAG
from app.domain.services.intent_evaluator import IntentEvaluatorService

# ---------- intent_evaluator 84->91: parsed but non-destructive ----------

def test_intent_evaluator_parse_one_raises_and_returns_none() -> None:
    """sqlglot.parse_one raises ParseError -> pass; then None returned."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="run",
        reasoning_step="step",
        proposed_tool="sql_query",
        tool_arguments={"query": "not valid sql statement"},
    )
    # _inspect_destructive_sql: no regex match, sqlglot raises ParseError -> None.
    assert evaluator._inspect_destructive_sql(intent) is None


def test_intent_evaluator_parser_none_is_not_destructive() -> None:
    """A parser with no statement result does not flag the action as destructive."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="run",
        reasoning_step="step",
        proposed_tool="sql_query",
        tool_arguments={"query": "SELECT * FROM users"},
    )
    with patch("app.domain.services.intent_evaluator.sqlglot.parse_one", return_value=None):
        assert evaluator._inspect_destructive_sql(intent) is None


def test_intent_evaluator_parse_deletion_with_where() -> None:
    """DELETE with WHERE: regex doesn't match, but parser detects it."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="clean row",
        reasoning_step="run SQL",
        proposed_tool="sql_query",
        tool_arguments={"query": "DELETE FROM users WHERE id = 5"},
    )
    result = evaluator.evaluate(intent)
    assert not result.is_valid
    assert "Destructive SQL" in result.reason


def test_intent_evaluator_select_query_not_destructive() -> None:
    """sqlglot parses; sql_type (SELECT) is not in destructive set -> None branch."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="Query data",
        reasoning_step="run",
        proposed_tool="sql_query",
        tool_arguments={"query": "SELECT * FROM users"},
    )
    result = evaluator._inspect_destructive_sql(intent)
    assert result is None


def test_intent_evaluator_insert_query_not_destructive() -> None:
    """sqlglot parses; sql_type (INSERT) is not in destructive set -> None branch."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="insert data",
        reasoning_step="run",
        proposed_tool="sql_query",
        tool_arguments={"query": "INSERT INTO table VALUES (1)"},
    )
    result = evaluator._inspect_destructive_sql(intent)
    assert result is None


def test_intent_evaluator_update_without_where_is_destructive() -> None:
    """UPDATE without WHERE is rejected by the destructive SQL guard."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="update record",
        reasoning_step="run",
        proposed_tool="sql_query",
        tool_arguments={"query": "UPDATE table SET x=1"},
    )
    result = evaluator._inspect_destructive_sql(intent)
    assert result == "Destructive SQL detected in proposed tool action."


# ---------- intent_evaluator 132-134: transfer amount from $ string on non-amount key ----------

def test_intent_evaluator_transfer_amount_from_dollar_string_other_key() -> None:
    """_extract_transfer_amount: a $ value in a non-amount key string."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="Send payment up to $500",
        reasoning_step="Send",
        proposed_tool="transfer_funds",
        tool_arguments={"attempt": 1, "note": "the cost is $400"},
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


def test_intent_evaluator_transfer_amount_skips_non_string_metadata() -> None:
    """Non-string metadata is ignored while a later dollar amount is extracted."""
    evaluator = IntentEvaluatorService()
    assert evaluator._extract_transfer_amount({"attempt": 1, "note": "cost $400"}) == 400.0


# ---------- intent_evaluator 178: ast.parse raises -> return False ----------

def test_intent_evaluator_ast_parse_fails_returns_false() -> None:
    """_contains_polyglot_payload: sqlglot fails, then ast.parse fails -> False."""
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


# ---------- intent_evaluator _extract_transfer_amount edge cases ----------

def test_intent_evaluator_transfer_amount_dollar_no_digit() -> None:
    """A non-amount dollar string does not produce a transfer amount."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="transfer money up to $100",
        reasoning_step="send",
        proposed_tool="transfer_funds",
        tool_arguments={"note": "$abc"},
    )
    result = evaluator.evaluate(intent)
    # $ without digit should not trigger transfer amount extraction
    assert result.is_valid


def test_intent_evaluator_transfer_amount_dollar_at_end() -> None:
    """_extract_transfer_amount: $ at end of string -> None."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="transfer money",
        reasoning_step="send",
        proposed_tool="transfer_funds",
        tool_arguments={"note": "cost $"},
    )
    result = evaluator.evaluate(intent)
    # $ at end should not trigger transfer amount extraction
    assert result.is_valid


def test_intent_evaluator_transfer_prompt_limit_exceeded() -> None:
    """Transfer amount exceeding prompt limit is blocked."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="Send up to $50",
        reasoning_step="send money",
        proposed_tool="transfer_funds",
        tool_arguments={"note": "the amount is $200"},
    )
    result = evaluator.evaluate(intent)
    assert not result.is_valid
    assert "exceeds the prompt limit" in result.reason


def test_intent_evaluator_transfer_within_prompt_limit() -> None:
    """Transfer amount within prompt limit is allowed."""
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        agent_id="a",
        user_prompt="Send up to $500",
        reasoning_step="send money",
        proposed_tool="transfer_funds",
        tool_arguments={"note": "the amount is $100"},
    )
    result = evaluator.evaluate(intent)
    assert result.is_valid
