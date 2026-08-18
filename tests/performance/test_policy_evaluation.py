import sys
import time

import pytest

from app.domain.models.intent import AgentActionDAG
from app.domain.services.intent_evaluator import IntentEvaluatorService


@pytest.fixture
def intent_evaluator() -> IntentEvaluatorService:
    return IntentEvaluatorService()


@pytest.fixture
def safe_intent() -> AgentActionDAG:
    return AgentActionDAG(
        user_prompt="List all users",
        agent_id="agent-bench-001",
        reasoning_step="Execute query_database",
        proposed_tool="query_database",
        tool_arguments={"query": "SELECT * FROM users LIMIT 10"},
    )


@pytest.fixture
def blocked_intent() -> AgentActionDAG:
    return AgentActionDAG(
        user_prompt="Delete all records",
        agent_id="agent-bench-001",
        reasoning_step="Execute destructive_sql",
        proposed_tool="destructive_sql",
        tool_arguments={"query": "DROP TABLE users"},
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Performance thresholds are platform-specific")
def test_policy_evaluation_latency_under_5ms(
    intent_evaluator: IntentEvaluatorService,
    safe_intent: AgentActionDAG,
) -> None:
    """Policy evaluation must complete in under 5ms on average for safe intents."""
    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        intent_evaluator.evaluate(safe_intent)
    elapsed = time.perf_counter() - start
    mean_latency_ms = (elapsed / iterations) * 1000

    assert mean_latency_ms < 5.0, (
        f"Policy evaluation latency {mean_latency_ms:.4f}ms exceeds 5ms threshold"
    )


def test_blocked_intent_evaluation_latency_under_5ms(
    intent_evaluator: IntentEvaluatorService,
    blocked_intent: AgentActionDAG,
) -> None:
    """Blocked intent evaluation must complete in under 5ms on average."""
    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        intent_evaluator.evaluate(blocked_intent)
    elapsed = time.perf_counter() - start
    mean_latency_ms = (elapsed / iterations) * 1000

    assert mean_latency_ms < 5.0, (
        f"Blocked intent evaluation latency {mean_latency_ms:.4f}ms exceeds 5ms threshold"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Performance thresholds are platform-specific")
def test_policy_evaluation_throughput_over_200_rps(
    intent_evaluator: IntentEvaluatorService,
    safe_intent: AgentActionDAG,
) -> None:
    """Policy evaluation must sustain over 200 evaluations per second."""
    iterations = 2000
    start = time.perf_counter()
    for _ in range(iterations):
        intent_evaluator.evaluate(safe_intent)
    elapsed = time.perf_counter() - start
    throughput = iterations / elapsed

    assert throughput > 200, (
        f"Policy evaluation throughput {throughput:.2f} rps below 200 rps threshold"
    )


def test_policy_evaluation_regression(
    intent_evaluator: IntentEvaluatorService,
    safe_intent: AgentActionDAG,
) -> None:
    """Track baseline policy evaluation latency for regression detection."""
    iterations = 500
    start = time.perf_counter()
    for _ in range(iterations):
        intent_evaluator.evaluate(safe_intent)
    elapsed = time.perf_counter() - start
    mean_latency_ms = (elapsed / iterations) * 1000

    result = {
        "operation": "policy_evaluation",
        "iterations": iterations,
        "mean_latency_ms": round(mean_latency_ms, 4),
        "throughput_per_second": round(iterations / elapsed, 2),
    }

    sys.stderr.write(f"Policy evaluation regression benchmark: {result}\n")
    assert mean_latency_ms < 20.0, "Regression: policy evaluation latency exceeded 20ms"
