from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domain.models.intent import AgentActionDAG
from app.domain.services.hitl_queue import HITLQueue
from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.domain.services.policy_engine import PolicyEngine
from app.domain.services.velocity_tracker import VelocityTracker


def test_policy_engine_simple_yaml_parsing(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test_policy.yaml"
    yaml_file.write_text(
        "# Comment line\n"
        "score_threshold: 0.6\n"
        "blocked_patterns:\n"
        "  - drop database\n"
        "  - rm -rf\n",
        encoding="utf-8",
    )

    with patch("app.domain.services.policy_engine.yaml", None):
        engine = PolicyEngine.from_file(yaml_file)
        assert engine.score_threshold == 0.6
        assert "drop database" in engine.blocked_patterns
        assert "rm -rf" in engine.blocked_patterns


def test_policy_engine_evaluation_branches() -> None:
    engine = PolicyEngine(score_threshold=0.5, blocked_patterns=["malicious_cmd"])

    # None / Empty
    res_empty = engine.evaluate("")
    assert not res_empty["blocked"]
    assert "No suspicious markers detected" in res_empty["reasons"]

    # Blocked pattern
    res_pat = engine.evaluate("run malicious_cmd here")
    assert res_pat["blocked"]
    assert any("Blocked pattern matched" in r for r in res_pat["reasons"])

    # Zero width unicode
    res_zw = engine.evaluate("hello\u200bworld")
    assert any("Zero-width unicode" in r for r in res_zw["reasons"])

    # Base64 payload
    res_b64 = engine.evaluate("payload SGVsbG8gV29ybGQh==")
    assert any("Base64 payload" in r for r in res_b64["reasons"])

    # Financial transfer pattern
    res_fin = engine.evaluate("please transfer $500 to alice")
    assert any("Financial transfer" in r for r in res_fin["reasons"])


def test_intent_evaluator_destructive_sql() -> None:
    evaluator = IntentEvaluatorService()

    # Regex destructive SQL
    intent_drop = AgentActionDAG(
        agent_id="agent-001",
        user_prompt="clean DB",
        reasoning_step="run SQL",
        proposed_tool="sql_query",
        tool_arguments={"query": "DROP TABLE users"},
    )
    res_drop = evaluator.evaluate(intent_drop)
    assert not res_drop.is_valid
    assert "Destructive SQL" in res_drop.reason or (
        "Tool argument validation failed" in res_drop.reason
    )

    # sqlglot parsed destructive SQL
    intent_truncate = AgentActionDAG(
        agent_id="agent-001",
        user_prompt="truncate data",
        reasoning_step="run SQL",
        proposed_tool="sql_query",
        tool_arguments={"query": "TRUNCATE TABLE audit_logs"},
    )
    res_trunc = evaluator.evaluate(intent_truncate)
    assert not res_trunc.is_valid


def test_intent_evaluator_financial_transfer_limits() -> None:
    evaluator = IntentEvaluatorService()

    # Prompt limit $100, transfer amount $500 -> rejected
    intent_over = AgentActionDAG(
        agent_id="agent-001",
        user_prompt="Send payment up to $100",
        reasoning_step="Execute transfer",
        proposed_tool="transfer_funds",
        tool_arguments={"amount": "$500.00"},
    )
    res_over = evaluator.evaluate(intent_over)
    assert not res_over.is_valid
    assert "exceeds the prompt limit" in res_over.reason

    # Prompt limit $1000, transfer amount $500 -> allowed
    intent_ok = AgentActionDAG(
        agent_id="agent-001",
        user_prompt="Send payment up to $1000",
        reasoning_step="Execute transfer",
        proposed_tool="transfer_funds",
        tool_arguments={"amount": 500},
    )
    res_ok = evaluator.evaluate(intent_ok)
    assert res_ok.is_valid


def test_intent_evaluator_polyglot_and_parse_helpers() -> None:
    evaluator = IntentEvaluatorService()

    # Shell echo / polyglot in prompt
    intent_poly = AgentActionDAG(
        agent_id="agent-001",
        user_prompt="echo 'pwned'",
        reasoning_step="exploit",
        proposed_tool="bash",
        tool_arguments={},
    )
    res_poly = evaluator.evaluate(intent_poly)
    assert not res_poly.is_valid

    # Polyglot parse exception branch (sqlglot / ast fail)
    intent_ast_fail = AgentActionDAG(
        agent_id="agent-001",
        user_prompt="1 + + + * invalid python syntax sql injection union select",
        reasoning_step="exploit",
        proposed_tool="bash",
        tool_arguments={},
    )
    assert not evaluator.evaluate(intent_ast_fail).is_valid

    # Policy engine violation return branch
    with patch.object(
        evaluator._policy_engine,
        "evaluate",
        return_value={"blocked": True, "risk_score": 0.85, "reasons": ["Custom block"]},
    ):
        intent_pol_block = AgentActionDAG(
            agent_id="agent-001",
            user_prompt="do action",
            reasoning_step="step",
            proposed_tool="tool",
            tool_arguments={},
        )
        res_pol_block = evaluator.evaluate(intent_pol_block)
        assert not res_pol_block.is_valid
        assert "Policy violation" in res_pol_block.reason

    # Non-transfer action tool argument key matching keyword
    intent_arg_key = AgentActionDAG(
        agent_id="agent-001",
        user_prompt="limit $50",
        reasoning_step="step",
        proposed_tool="custom_tool",
        tool_arguments={"transfer_amount": "$100"},
    )
    assert not evaluator.evaluate(intent_arg_key).is_valid

    # Prompt limit exists but non-transfer tool arguments without transfer keyword -> returns None
    intent_no_tr = AgentActionDAG(
        agent_id="agent-001",
        user_prompt="limit $50",
        reasoning_step="step",
        proposed_tool="read_file",
        tool_arguments={"path": "safe/path"},
    )
    assert evaluator.evaluate(intent_no_tr).is_valid

    # Amount parser helpers
    assert evaluator._parse_amount(None) is None
    assert evaluator._parse_amount("invalid") is None
    assert evaluator._parse_amount(100) == 100.0
    assert evaluator._parse_amount("1,250.50") == 1250.50

    # Collect strings helper
    assert evaluator._collect_strings({"a": ["hello", {"b": "world"}], "c": 123}) == [
        "hello",
        "world",
    ]


def test_hitl_queue_full_coverage() -> None:
    # Redis exception handling in enqueue_request
    mock_redis = MagicMock()
    mock_redis.set.side_effect = Exception("Redis error")
    queue = HITLQueue(ttl_seconds=300, redis_client=mock_redis)

    req_id = None
    import asyncio
    async def run_hitl():
        nonlocal req_id
        req_id = await queue.enqueue_request(intent_text="action", risk_score=0.9)
        # Approve and reject
        appr_entry = await queue.approve_request(req_id)
        assert appr_entry["status"] == "approved"

        req_id2 = await queue.enqueue_request(intent_text="action2", risk_score=0.9)
        rej_entry = await queue.reject_request(req_id2)
        assert rej_entry["status"] == "rejected"

        queue.reset()
        assert len(await queue.list_pending_requests()) == 0

    asyncio.run(run_hitl())


def test_velocity_tracker_limits_and_pruning() -> None:
    tracker = VelocityTracker(
        window_seconds=1,
        max_requests=2,
        max_cumulative_value=100.0,
        max_cumulative_risk=1.0,
        max_sensitive_operations=1,
    )

    # Record normal
    st1 = tracker.record(scope="agent1", value=50.0, risk_score=0.4, is_sensitive=True)
    assert not st1["blocked"]

    # Exceed requests and sensitive ops
    st2 = tracker.record(scope="agent1", value=60.0, risk_score=0.8, is_sensitive=True)
    assert st2["blocked"]
    assert any(
        "Request velocity" in r or "Cumulative value" in r or "Sensitive operations" in r
        for r in st2["reasons"]
    )

    # Get state
    st_get = tracker.get_state("agent1")
    assert st_get["blocked"]

    # Nonexistent scope state
    assert tracker.get_state("ghost")["request_count"] == 0

    # Reset scope
    tracker.reset("agent1")
    assert tracker.get_state("agent1")["request_count"] == 0

    # Reset all
    tracker.record(scope="a2", value=10.0)
    tracker.reset()
    assert tracker.get_state("a2")["request_count"] == 0


@pytest.mark.asyncio
async def test_hitl_queue_redis_and_eviction() -> None:
    mock_redis = MagicMock()
    queue = HITLQueue(ttl_seconds=1, redis_client=mock_redis)

    await queue.enqueue_request(intent_text="action", risk_score=0.9)
    mock_redis.set.assert_called_once()

    # Wait for expiration
    import asyncio
    await asyncio.sleep(1.1)

    # List pending should evict expired request
    pending = await queue.list_pending_requests()
    assert len(pending) == 0
