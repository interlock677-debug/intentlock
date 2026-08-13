from app.domain.services.policy_engine import PolicyEngine


def test_policy_engine_blocks_pattern() -> None:
    engine = PolicyEngine(score_threshold=0.5, blocked_patterns=["drop table"])
    result = engine.evaluate("DROP TABLE users;")
    assert result["blocked"] is True
    assert "Blocked pattern matched" in result["reasons"][0]


def test_policy_engine_allows_safe_text() -> None:
    engine = PolicyEngine(score_threshold=0.5, blocked_patterns=[])
    result = engine.evaluate("Please process this invoice.")
    assert result["blocked"] is False
    assert result["risk_score"] == 0.0


def test_policy_engine_detects_zero_width() -> None:
    engine = PolicyEngine(score_threshold=0.35, blocked_patterns=[])
    payload = "normal\u200bpayload"
    result = engine.evaluate(payload)
    assert result["blocked"] is True
    assert any("Zero-width" in reason for reason in result["reasons"])


def test_policy_engine_detects_base64() -> None:
    engine = PolicyEngine(score_threshold=0.35, blocked_patterns=[])
    payload = "YWJjZGVm=="
    result = engine.evaluate(payload)
    assert result["blocked"] is True
    assert any("Base64" in reason for reason in result["reasons"])


def test_policy_engine_sliding_threshold() -> None:
    engine = PolicyEngine(score_threshold=0.6, blocked_patterns=[])
    # No markers => score 0.0 => not blocked
    result = engine.evaluate("safe text")
    assert result["blocked"] is False
    # One zero-width marker => score 0.35 => not blocked
    result = engine.evaluate("safe\u200btest")
    assert result["blocked"] is False
    # Base64 marker => score 0.35 => not blocked
    result = engine.evaluate("safeYWJjZGVm==")
    assert result["blocked"] is False
    # Both zero-width and base64 => score 0.7 => blocked
    result = engine.evaluate("safe\u200btestYWJjZGVm==")
    assert result["blocked"] is True


def test_policy_engine_negative_threshold_allowed() -> None:
    # Threshold is accepted as-is; negative values effectively disable blocking
    engine = PolicyEngine(score_threshold=-1.0, blocked_patterns=[])
    assert engine.score_threshold == -1.0


