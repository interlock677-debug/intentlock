from app.application.interfaces.event_bus import (
    AuthorizationDeniedEvent,
    HITLEvent,
    NoOpSecurityEventBus,
    PolicyDecisionEvent,
    SecurityEventBus,
    SecurityExceptionEvent,
)


def test_authorization_denied_event_defaults() -> None:
    event = AuthorizationDeniedEvent(
        agent_id="agent-1",
        proposed_tool="search",
        reason="denied",
    )
    assert event.agent_id == "agent-1"
    assert event.proposed_tool == "search"
    assert event.reason == "denied"
    assert event.correlation_id == ""


def test_authorization_denied_event_with_correlation_id() -> None:
    event = AuthorizationDeniedEvent(
        agent_id="agent-1",
        proposed_tool="search",
        reason="denied",
        correlation_id="corr-123",
    )
    assert event.correlation_id == "corr-123"


def test_hitl_event_defaults() -> None:
    event = HITLEvent(
        request_id="req-1",
        event_type="approved",
    )
    assert event.request_id == "req-1"
    assert event.event_type == "approved"
    assert event.decided_by is None
    assert event.risk_score is None
    assert event.correlation_id == ""


def test_hitl_event_with_all_fields() -> None:
    event = HITLEvent(
        request_id="req-1",
        event_type="approved",
        decided_by="user-1",
        risk_score=0.5,
        correlation_id="corr-123",
    )
    assert event.decided_by == "user-1"
    assert event.risk_score == 0.5
    assert event.correlation_id == "corr-123"


def test_policy_decision_event_defaults() -> None:
    event = PolicyDecisionEvent(
        rule_id="rule-1",
        effect="deny",
        reason="blocked",
    )
    assert event.rule_id == "rule-1"
    assert event.effect == "deny"
    assert event.reason == "blocked"
    assert event.agent_id == ""
    assert event.proposed_tool == ""
    assert event.correlation_id == ""


def test_policy_decision_event_with_identities() -> None:
    event = PolicyDecisionEvent(
        rule_id="rule-1",
        effect="deny",
        reason="blocked",
        agent_id="agent-1",
        proposed_tool="search",
        correlation_id="corr-123",
    )
    assert event.agent_id == "agent-1"
    assert event.proposed_tool == "search"
    assert event.correlation_id == "corr-123"


def test_security_exception_event_defaults() -> None:
    event = SecurityExceptionEvent(
        exception_type="ValueError",
        message="invalid input",
    )
    assert event.exception_type == "ValueError"
    assert event.message == "invalid input"
    assert event.correlation_id == ""


def test_security_exception_event_with_correlation_id() -> None:
    event = SecurityExceptionEvent(
        exception_type="ValueError",
        message="invalid input",
        correlation_id="corr-123",
    )
    assert event.correlation_id == "corr-123"


def test_noop_security_event_bus_publish_authorization_denied() -> None:
    bus = NoOpSecurityEventBus()
    event = AuthorizationDeniedEvent(
        agent_id="agent-1",
        proposed_tool="search",
        reason="denied",
    )
    bus.publish_authorization_denied(event)


def test_noop_security_event_bus_publish_hitl_event() -> None:
    bus = NoOpSecurityEventBus()
    event = HITLEvent(
        request_id="req-1",
        event_type="approved",
    )
    bus.publish_hitl_event(event)


def test_noop_security_event_bus_publish_policy_decision() -> None:
    bus = NoOpSecurityEventBus()
    event = PolicyDecisionEvent(
        rule_id="rule-1",
        effect="deny",
        reason="blocked",
    )
    bus.publish_policy_decision(event)


def test_noop_security_event_bus_publish_security_exception() -> None:
    bus = NoOpSecurityEventBus()
    event = SecurityExceptionEvent(
        exception_type="ValueError",
        message="invalid input",
    )
    bus.publish_security_exception(event)


def test_security_event_bus_is_abstract() -> None:
    assert issubclass(SecurityEventBus, type) or hasattr(SecurityEventBus, "__abstractmethods__")
