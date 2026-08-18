import threading

import pytest

from app.infrastructure.observability.metrics import SecurityMetrics


@pytest.fixture
def metrics_instance() -> SecurityMetrics:
    return SecurityMetrics()


def test_increment_authorization_denials(metrics_instance: SecurityMetrics) -> None:
    metrics_instance.increment_authorization_denial("tool_denied")
    metrics_instance.increment_authorization_denial("tool_denied")
    metrics_instance.increment_authorization_denial("tenant_invalid")
    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["authorization_denials_total"] == 3
    assert snapshot["authorization_denials"]["tool_denied"] == 2
    assert snapshot["authorization_denials"]["tenant_invalid"] == 1


def test_increment_hitl_events(metrics_instance: SecurityMetrics) -> None:
    metrics_instance.increment_hitl_event("approved")
    metrics_instance.increment_hitl_event("rejected")
    metrics_instance.increment_hitl_event("approved")
    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["hitl_events_total"] == 3
    assert snapshot["hitl_events"]["approved"] == 2
    assert snapshot["hitl_events"]["rejected"] == 1


def test_increment_policy_decisions(metrics_instance: SecurityMetrics) -> None:
    metrics_instance.increment_policy_decision("allow")
    metrics_instance.increment_policy_decision("deny")
    metrics_instance.increment_policy_decision("allow")
    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["policy_decisions_total"] == 3
    assert snapshot["policy_decisions"]["allow"] == 2
    assert snapshot["policy_decisions"]["deny"] == 1


def test_increment_suspicious_tool_calls(metrics_instance: SecurityMetrics) -> None:
    metrics_instance.increment_suspicious_tool_call("sql_injection")
    metrics_instance.increment_suspicious_tool_call("prompt_injection")
    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["suspicious_tool_calls_total"] == 2
    assert snapshot["suspicious_tool_calls"]["sql_injection"] == 1
    assert snapshot["suspicious_tool_calls"]["prompt_injection"] == 1


def test_increment_authentication_failures(metrics_instance: SecurityMetrics) -> None:
    metrics_instance.increment_authentication_failure("invalid_credentials")
    metrics_instance.increment_authentication_failure("account_locked")
    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["authentication_failures_total"] == 2
    assert snapshot["authentication_failures"]["invalid_credentials"] == 1


def test_increment_security_exceptions(metrics_instance: SecurityMetrics) -> None:
    metrics_instance.increment_security_exception("TokenError")
    metrics_instance.increment_security_exception("TokenError")
    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["security_exceptions_total"] == 2
    assert snapshot["security_exceptions"]["TokenError"] == 2


def test_increment_execution_tokens(metrics_instance: SecurityMetrics) -> None:
    metrics_instance.increment_execution_tokens_issued()
    metrics_instance.increment_execution_tokens_issued()
    metrics_instance.increment_execution_tokens_consumed()
    metrics_instance.increment_execution_tokens_replayed()
    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["execution_tokens_issued"] == 2
    assert snapshot["execution_tokens_consumed"] == 1
    assert snapshot["execution_tokens_replayed"] == 1


def test_reset_clears_all_counters(metrics_instance: SecurityMetrics) -> None:
    metrics_instance.increment_authorization_denial("tool_denied")
    metrics_instance.increment_hitl_event("approved")
    metrics_instance.increment_policy_decision("deny")
    metrics_instance.increment_execution_tokens_issued()
    metrics_instance.reset()
    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["authorization_denials_total"] == 0
    assert snapshot["hitl_events_total"] == 0
    assert snapshot["policy_decisions_total"] == 0
    assert snapshot["execution_tokens_issued"] == 0
    assert snapshot["execution_tokens_consumed"] == 0
    assert snapshot["execution_tokens_replayed"] == 0


def test_thread_safety(metrics_instance: SecurityMetrics) -> None:
    def incrementer() -> None:
        for _ in range(100):
            metrics_instance.increment_authorization_denial("tool_denied")
            metrics_instance.increment_hitl_event("approved")
            metrics_instance.increment_execution_tokens_issued()

    threads = [threading.Thread(target=incrementer) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    snapshot = metrics_instance.get_metrics_snapshot()
    assert snapshot["authorization_denials_total"] == 1000
    assert snapshot["hitl_events_total"] == 1000
    assert snapshot["execution_tokens_issued"] == 1000
