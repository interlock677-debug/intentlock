import sys
import time

import pytest

from app.domain.services.authorization_service import AuthorizationService
from app.domain.value_objects.authorization_context import AuthorizationContext


@pytest.fixture
def authorization_service() -> AuthorizationService:
    return AuthorizationService()


@pytest.fixture
def auth_context() -> AuthorizationContext:
    return AuthorizationContext(
        user_id="user-bench-123",
        agent_id="agent-bench-001",
        proposed_tool="query_database",
        tenant_id="tenant-bench-001",
        action="read",
        resource="users",
    )


def test_authorization_latency_under_1ms(
    authorization_service: AuthorizationService,
    auth_context: AuthorizationContext,
) -> None:
    """Authorization decisions must complete in under 1ms on average."""
    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        authorization_service.authorize(auth_context)
    elapsed = time.perf_counter() - start
    mean_latency_ms = (elapsed / iterations) * 1000

    assert mean_latency_ms < 1.0, (
        f"Authorization latency {mean_latency_ms:.4f}ms exceeds 1ms threshold"
    )


def test_authorization_throughput_over_1000_rps(
    authorization_service: AuthorizationService,
    auth_context: AuthorizationContext,
) -> None:
    """Authorization must sustain over 1000 decisions per second."""
    iterations = 5000
    start = time.perf_counter()
    for _ in range(iterations):
        authorization_service.authorize(auth_context)
    elapsed = time.perf_counter() - start
    throughput = iterations / elapsed

    assert throughput > 1000, (
        f"Authorization throughput {throughput:.2f} rps below 1000 rps threshold"
    )


def test_authorization_latency_regression(
    authorization_service: AuthorizationService,
    auth_context: AuthorizationContext,
) -> None:
    """Track baseline authorization latency for regression detection."""
    iterations = 500
    start = time.perf_counter()
    for _ in range(iterations):
        authorization_service.authorize(auth_context)
    elapsed = time.perf_counter() - start
    mean_latency_ms = (elapsed / iterations) * 1000

    result = {
        "operation": "authorization_decision",
        "iterations": iterations,
        "mean_latency_ms": round(mean_latency_ms, 4),
        "throughput_per_second": round(iterations / elapsed, 2),
    }

    sys.stderr.write(f"Authorization regression benchmark: {result}\n")
    assert mean_latency_ms < 5.0, "Regression: authorization latency exceeded 5ms"
