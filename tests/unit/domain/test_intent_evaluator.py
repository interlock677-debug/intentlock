from app.domain.models.intent import AgentActionDAG
from app.domain.services.intent_evaluator import IntentEvaluatorService


def test_intent_evaluator_accepts_safe_action() -> None:
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        user_prompt="Transfer up to $100 to vendor account",
        agent_id="agent-123",
        reasoning_step="Decide payment",
        proposed_tool="transfer_funds",
        tool_arguments={"amount": 50, "recipient": "vendor-abc"},
    )

    result = evaluator.evaluate(intent)

    assert result.is_valid
    assert result.confidence_score > 0.9
    assert result.ephemeral_token is None


def test_intent_evaluator_rejects_destructive_sql() -> None:
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        user_prompt="Please run the SQL query",
        agent_id="agent-123",
        reasoning_step="Prepare database cleanup",
        proposed_tool="execute_sql",
        tool_arguments={"query": "DROP TABLE users;"},
    )

    result = evaluator.evaluate(intent)

    assert not result.is_valid
    assert "Destructive SQL" in result.reason


def test_intent_evaluator_rejects_overlimit_transfer() -> None:
    evaluator = IntentEvaluatorService()
    intent = AgentActionDAG(
        user_prompt="Transfer no more than $100",
        agent_id="agent-123",
        reasoning_step="Send payment",
        proposed_tool="transfer_funds",
        tool_arguments={"amount": 150, "recipient": "vendor-abc"},
    )

    result = evaluator.evaluate(intent)

    assert not result.is_valid
    assert "exceeds the prompt limit" in result.reason
