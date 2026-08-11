import pytest

from app.domain.exceptions.domain_errors import ApprovalError
from app.domain.services.hitl_queue import HITLQueue


async def test_enqueue_and_list() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)
    pending = await queue.list_pending_requests()
    assert len(pending) == 1
    assert pending[0]["request_id"] == request_id
    assert pending[0]["status"] == "pending"


async def test_approve_request() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)
    entry = await queue.approve_request(request_id)
    assert entry["status"] == "approved"
    assert "decided_at" in entry

    # After approval, it should no longer be pending
    pending = await queue.list_pending_requests()
    assert len(pending) == 0


async def test_reject_request() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)
    entry = await queue.reject_request(request_id)
    assert entry["status"] == "rejected"
    assert "decided_at" in entry


async def test_approve_missing_request_raises() -> None:
    queue = HITLQueue(ttl_seconds=300)
    with pytest.raises(ApprovalError):
        await queue.approve_request("nonexistent")


async def test_approve_expired_request_raises() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)
    # Force expiration by setting expires_at in the past
    entry = queue._pending[request_id]  # type: ignore[attr-defined]
    from datetime import UTC, datetime, timedelta

    entry["expires_at"] = (datetime.now(tz=UTC) - timedelta(seconds=1)).isoformat()

    with pytest.raises(ApprovalError):
        await queue.approve_request(request_id)


async def test_cannot_approve_twice() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)
    await queue.approve_request(request_id)
    with pytest.raises(ApprovalError):
        await queue.approve_request(request_id)


async def test_reset_clears_queue() -> None:
    queue = HITLQueue(ttl_seconds=300)
    await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)
    queue.reset()
    pending = await queue.list_pending_requests()
    assert len(pending) == 0
