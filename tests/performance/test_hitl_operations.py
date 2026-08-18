import sys
import time

import pytest

from app.domain.services.hitl_queue import HITLQueue


@pytest.fixture
def hitl_queue() -> HITLQueue:
    return HITLQueue()


async def _enqueue_n(queue: HITLQueue, count: int) -> list[str]:
    request_ids = []
    for i in range(count):
        request_id = await queue.enqueue_request(
            intent_text=f"Transfer ${i}",
            risk_score=0.5,
        )
        request_ids.append(request_id)
    return request_ids


async def test_hitl_enqueue_latency_under_10ms(hitl_queue: HITLQueue) -> None:
    """HITL enqueue must complete in under 10ms on average."""
    iterations = 100
    start = time.perf_counter()
    await _enqueue_n(hitl_queue, iterations)
    elapsed = time.perf_counter() - start
    mean_latency_ms = (elapsed / iterations) * 1000

    assert mean_latency_ms < 10.0, (
        f"HITL enqueue latency {mean_latency_ms:.4f}ms exceeds 10ms threshold"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Performance thresholds are platform-specific")
async def test_hitl_list_pending_latency_under_5ms(hitl_queue: HITLQueue) -> None:
    """HITL list pending must complete in under 5ms on average."""
    await _enqueue_n(hitl_queue, 20)

    iterations = 50
    start = time.perf_counter()
    for _ in range(iterations):
        await hitl_queue.list_pending_requests()
    elapsed = time.perf_counter() - start
    mean_latency_ms = (elapsed / iterations) * 1000

    assert mean_latency_ms < 5.0, (
        f"HITL list pending latency {mean_latency_ms:.4f}ms exceeds 5ms threshold"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Performance thresholds are platform-specific")
async def test_hitl_approve_latency_under_10ms(hitl_queue: HITLQueue) -> None:
    """HITL approve must complete in under 10ms on average."""
    request_ids = await _enqueue_n(hitl_queue, 10)

    start = time.perf_counter()
    for request_id in request_ids:
        await hitl_queue.approve_request(request_id)
    elapsed = time.perf_counter() - start
    mean_latency_ms = (elapsed / len(request_ids)) * 1000

    assert mean_latency_ms < 10.0, (
        f"HITL approve latency {mean_latency_ms:.4f}ms exceeds 10ms threshold"
    )


async def test_hitl_throughput_over_100_ops_per_second(hitl_queue: HITLQueue) -> None:
    """HITL enqueue must sustain over 100 operations per second."""
    iterations = 200
    start = time.perf_counter()
    await _enqueue_n(hitl_queue, iterations)
    elapsed = time.perf_counter() - start
    throughput: float = iterations / elapsed
    assert throughput > 100, (
        f"HITL enqueue throughput {throughput:.2f} ops/sec below 100 ops/sec threshold"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Performance thresholds are platform-specific")
async def test_hitl_operations_regression(hitl_queue: HITLQueue) -> None:
    """Track baseline HITL operation latency for regression detection."""
    request_ids = await _enqueue_n(hitl_queue, 20)

    start = time.perf_counter()
    for _request_id in request_ids:
        await hitl_queue.list_pending_requests()
    list_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    for request_id in request_ids:
        await hitl_queue.approve_request(request_id, decided_by=None)
    approve_elapsed = time.perf_counter() - start

    list_mean: float = round((list_elapsed / len(request_ids)) * 1000, 4)
    approve_mean: float = round((approve_elapsed / len(request_ids)) * 1000, 4)
    result = {
        "operation": "hitl_operations",
        "list_pending_mean_ms": list_mean,
        "approve_mean_ms": approve_mean,
    }

    sys.stderr.write(f"HITL regression benchmark: {result}\n")
    assert list_mean < 10.0, "Regression: HITL list latency exceeded 10ms"
    assert approve_mean < 20.0, "Regression: HITL approve latency exceeded 20ms"
