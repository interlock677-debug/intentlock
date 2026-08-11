from app.domain.services.velocity_tracker import VelocityTracker


def test_initial_state_not_blocked() -> None:
    tracker = VelocityTracker()
    state = tracker.get_state("agent-1")
    assert state["blocked"] is False


def test_request_velocity_blocked() -> None:
    tracker = VelocityTracker(max_requests=2, window_seconds=60)
    tracker.record(scope="agent-1")
    tracker.record(scope="agent-1")
    state = tracker.record(scope="agent-1")
    assert state["blocked"] is True
    assert "Request velocity exceeded" in state["reasons"][0]


def test_cumulative_value_blocked() -> None:
    tracker = VelocityTracker(max_cumulative_value=100.0, window_seconds=60)
    tracker.record(scope="agent-1", value=60.0)
    state = tracker.record(scope="agent-1", value=60.0)
    assert state["blocked"] is True
    assert any("Cumulative value exceeded" in reason for reason in state["reasons"])


def test_cumulative_risk_blocked() -> None:
    tracker = VelocityTracker(max_cumulative_risk=1.0, window_seconds=60)
    tracker.record(scope="agent-1", risk_score=0.6)
    state = tracker.record(scope="agent-1", risk_score=0.6)
    assert state["blocked"] is True
    assert any("Cumulative risk exceeded" in reason for reason in state["reasons"])


def test_sensitive_operations_blocked() -> None:
    tracker = VelocityTracker(max_sensitive_operations=1, window_seconds=60)
    tracker.record(scope="agent-1", is_sensitive=True)
    state = tracker.record(scope="agent-1", is_sensitive=True)
    assert state["blocked"] is True
    assert any("Sensitive operations exceeded" in reason for reason in state["reasons"])


def test_scoped_independently() -> None:
    tracker = VelocityTracker(max_requests=1, window_seconds=60)
    tracker.record(scope="agent-1")
    state = tracker.record(scope="agent-1")
    assert state["blocked"] is True

    # A different scope should not be affected
    state2 = tracker.record(scope="agent-2")
    assert state2["blocked"] is False


def test_reset_clears_state() -> None:
    tracker = VelocityTracker(max_requests=1, window_seconds=60)
    tracker.record(scope="agent-1")
    tracker.reset(scope="agent-1")
    state = tracker.get_state("agent-1")
    assert state["blocked"] is False
