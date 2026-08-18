import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import init_db

get_settings.cache_clear()
init_db()

# Drop and recreate tables to ensure schema is up to date.
from app.infrastructure.persistence.database import Base, engine
Base.metadata.drop_all(bind=engine)
init_db()

from app.domain.services.authorization_service import AuthorizationService
from app.domain.services.hitl_queue import HITLQueue
from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.domain.value_objects.authorization_context import AuthorizationContext


def benchmark_authz_latency(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark authorization decision latency."""
    service = AuthorizationService()
    context = AuthorizationContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        agent_id="agent-001",
        proposed_tool="query_database",
        tenant_id="tenant-001",
    )

    start = time.perf_counter()
    for _ in range(iterations):
        service.authorize(context)
    elapsed = time.perf_counter() - start

    return {
        "operation": "authorization_decision",
        "iterations": iterations,
        "total_seconds": round(elapsed, 4),
        "mean_latency_ms": round((elapsed / iterations) * 1000, 4),
        "throughput_per_second": round(iterations / elapsed, 2),
    }


def benchmark_policy_evaluation(iterations: int = 1000) -> dict[str, Any]:
    """Benchmark policy evaluation latency."""
    evaluator = IntentEvaluatorService()
    from app.domain.models.intent import AgentActionDAG

    intent = AgentActionDAG(
        user_prompt="List all users",
        agent_id="agent-001",
        reasoning_step="Execute query_database",
        proposed_tool="query_database",
        tool_arguments={"query": "SELECT * FROM users"},
    )

    start = time.perf_counter()
    for _ in range(iterations):
        evaluator.evaluate(intent)
    elapsed = time.perf_counter() - start

    return {
        "operation": "policy_evaluation",
        "iterations": iterations,
        "total_seconds": round(elapsed, 4),
        "mean_latency_ms": round((elapsed / iterations) * 1000, 4),
        "throughput_per_second": round(iterations / elapsed, 2),
    }


async def benchmark_hitl_operations(iterations: int = 100) -> dict[str, Any]:
    """Benchmark HITL enqueue/approve/list latency."""
    queue = HITLQueue()

    # Enqueue
    start = time.perf_counter()
    request_ids: list[str] = []
    for i in range(iterations):
        request_id = await queue.enqueue_request(
            intent_text=f"Transfer ${i}",
            risk_score=0.5,
        )
        request_ids.append(request_id)
    enqueue_elapsed = time.perf_counter() - start

    # List pending
    start = time.perf_counter()
    for _ in range(iterations // 10 or 1):
        await queue.list_pending_requests()
    list_elapsed = time.perf_counter() - start

    # Approve
    start = time.perf_counter()
    for request_id in request_ids[: min(10, iterations)]:
        await queue.approve_request(request_id, decided_by=None)
    approve_elapsed = time.perf_counter() - start

    return {
        "operation": "hitl_operations",
        "iterations": iterations,
        "enqueue": {
            "total_seconds": round(enqueue_elapsed, 4),
            "mean_latency_ms": round(
                (enqueue_elapsed / iterations) * 1000, 4
            ),
            "throughput_per_second": round(iterations / enqueue_elapsed, 2),
        },
        "list_pending": {
            "total_seconds": round(list_elapsed, 4),
            "calls": max(iterations // 10, 1),
            "mean_latency_ms": round(
                (list_elapsed / max(iterations // 10, 1)) * 1000, 4
            ),
        },
        "approve": {
            "total_seconds": round(approve_elapsed, 4),
            "operations": min(10, iterations),
            "mean_latency_ms": round(
                (approve_elapsed / min(10, iterations)) * 1000, 4
            ),
        },
    }


def run_all_benchmarks() -> dict[str, Any]:
    """Run all benchmarks and return results."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        hitl_result = loop.run_until_complete(
            benchmark_hitl_operations()
        )
    finally:
        loop.close()

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": sys.version,
        "benchmarks": [
            benchmark_authz_latency(),
            benchmark_policy_evaluation(),
            hitl_result,
        ],
    }
    return results


def save_results(results: dict[str, Any], output_path: str = "benchmark_results.json") -> None:
    """Save benchmark results to a JSON file."""
    path = Path(output_path)
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    sys.stderr.write(f"Results saved to {output_path}\n")


def compare_with_baseline(
    current: dict[str, Any], baseline_path: str = "benchmark_baseline.json"
) -> None:
    """Compare current results with a baseline."""
    baseline_file = Path(baseline_path)
    if not baseline_file.exists():
        sys.stderr.write(
            f"No baseline found at {baseline_path}. Skipping comparison.\n"
        )
        return

    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    sys.stderr.write("\n=== Baseline Comparison ===\n")
    for bench in current.get("benchmarks", []):
        op = bench.get("operation")
        for base in baseline.get("benchmarks", []):
            if base.get("operation") == op:
                current_mean = bench.get("mean_latency_ms", 0)
                baseline_mean = base.get("mean_latency_ms", 0)
                if baseline_mean > 0:
                    change = (
                        (current_mean - baseline_mean) / baseline_mean
                    ) * 100
                    direction = "FASTER" if change < 0 else "SLOWER"
                    sys.stderr.write(
                        f"{op}: {abs(change):.1f}% {direction} "
                        f"(current: {current_mean:.4f}ms, "
                        f"baseline: {baseline_mean:.4f}ms)\n"
                    )
                break


def main() -> None:
    results = run_all_benchmarks()
    save_results(results)
    compare_with_baseline(results)

    sys.stderr.write("\n=== Summary ===\n")
    for bench in results.get("benchmarks", []):
        sys.stderr.write(
            f"{bench.get('operation')}: "
            f"{bench.get('mean_latency_ms', 'N/A')}ms avg\n"
        )


if __name__ == "__main__":
    main()
