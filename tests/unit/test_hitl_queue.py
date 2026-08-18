from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.domain.exceptions.domain_errors import ApprovalError
from app.domain.services.hitl_queue import HITLQueue
from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.persistence.models.approval_request_model import ApprovalRequestModel


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
    with get_db_session() as session:
        model = session.scalar(
            select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == request_id)
        )
        assert model is not None
        model.expires_at = datetime.now(tz=UTC) - timedelta(seconds=1)

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


# ---------- Phase 5: durable HITL regression tests ----------


async def test_request_persisted_to_database() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)

    with get_db_session() as session:
        model = session.scalar(
            select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == request_id)
        )
        assert model is not None
        assert model.status == "pending"
        assert model.intent_text == "transfer funds"
        assert model.risk_score == 0.7


async def test_duplicate_rejection_raises() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)
    await queue.reject_request(request_id)
    with pytest.raises(ApprovalError):
        await queue.reject_request(request_id)


async def test_reject_already_approved_raises() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)
    await queue.approve_request(request_id)
    with pytest.raises(ApprovalError):
        await queue.reject_request(request_id)


async def test_duplicate_request_id_raises() -> None:
    queue = HITLQueue(ttl_seconds=300)
    await queue.enqueue_request(request_id="fixed-id", intent_text="transfer funds", risk_score=0.7)
    with pytest.raises(ApprovalError):
        await queue.enqueue_request(request_id="fixed-id", intent_text="another", risk_score=0.5)


async def test_persists_across_instances() -> None:
    queue1 = HITLQueue(ttl_seconds=300)
    request_id = await queue1.enqueue_request(intent_text="transfer funds", risk_score=0.7)

    # A new queue instance (simulating another process/instance) sees the same data.
    queue2 = HITLQueue(ttl_seconds=300)
    pending = await queue2.list_pending_requests()
    assert [p["request_id"] for p in pending] == [request_id]

    entry = await queue2.approve_request(request_id)
    assert entry["status"] == "approved"

    # queue1 also sees the approved state (no longer pending).
    pending1 = await queue1.list_pending_requests()
    assert len(pending1) == 0


async def test_database_failure_does_not_approve() -> None:
    from unittest.mock import patch

    from app.domain.services import hitl_queue as hitl_module

    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)

    with patch.object(
        hitl_module, "get_db_session", side_effect=RuntimeError("db down")
    ), pytest.raises(RuntimeError):
        await queue.approve_request(request_id)

    # The request must still be pending (not approved).
    pending = await queue.list_pending_requests()
    assert [p["request_id"] for p in pending] == [request_id]
    assert pending[0]["status"] == "pending"


async def test_transaction_rollback_prevents_approval() -> None:
    from unittest.mock import MagicMock

    from app.infrastructure.persistence import database

    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(intent_text="transfer funds", risk_score=0.7)

    original = database.SessionLocal
    fake_session = MagicMock()
    fake_session.__enter__.return_value = fake_session
    fake_session.commit.side_effect = RuntimeError("commit failed")
    fake_session.scalar.return_value = ApprovalRequestModel(
        request_id=request_id,
        intent_text="transfer funds",
        risk_score=0.7,
        status="pending",
        created_at=datetime.now(tz=UTC),
        expires_at=datetime.now(tz=UTC) + timedelta(seconds=300),
    )
    database.SessionLocal = MagicMock(return_value=fake_session)
    try:
        with pytest.raises(RuntimeError):
            await queue.approve_request(request_id)
    finally:
        database.SessionLocal = original

    fake_session.rollback.assert_called_once()
    # The request must still be pending (not approved).
    pending = await queue.list_pending_requests()
    assert [p["request_id"] for p in pending] == [request_id]
    assert pending[0]["status"] == "pending"


# ---------- Tenant scoping tests ----------


async def test_enqueue_request_stores_tenant_id() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(
        intent_text="transfer funds",
        risk_score=0.7,
        tenant_id="tenant-1",
        user_id=uuid4(),
    )

    with get_db_session() as session:
        model = session.scalar(
            select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == request_id)
        )
        assert model is not None
        assert model.tenant_id == "tenant-1"
        assert model.user_id is not None


async def test_list_pending_requests_filters_by_tenant() -> None:
    queue = HITLQueue(ttl_seconds=300)
    req_id1 = await queue.enqueue_request(
        intent_text="tenant1", risk_score=0.7, tenant_id="tenant-1"
    )
    await queue.enqueue_request(
        intent_text="tenant2", risk_score=0.7, tenant_id="tenant-2"
    )
    await queue.enqueue_request(intent_text="notenant", risk_score=0.7)

    pending = await queue.list_pending_requests(tenant_id="tenant-1")
    assert len(pending) == 1
    assert pending[0]["request_id"] == req_id1


async def test_list_pending_requests_returns_all_when_no_tenant_filter() -> None:
    queue = HITLQueue(ttl_seconds=300)
    await queue.enqueue_request(intent_text="tenant1", risk_score=0.7, tenant_id="tenant-1")
    await queue.enqueue_request(intent_text="tenant2", risk_score=0.7, tenant_id="tenant-2")

    pending = await queue.list_pending_requests()
    assert len(pending) == 2


async def test_cross_tenant_approve_raises() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(
        intent_text="transfer funds", risk_score=0.7, tenant_id="tenant-1"
    )

    with pytest.raises(ApprovalError, match="does not belong to tenant"):
        await queue.approve_request(request_id, tenant_id="tenant-2")


async def test_cross_tenant_reject_raises() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(
        intent_text="transfer funds", risk_score=0.7, tenant_id="tenant-1"
    )

    with pytest.raises(ApprovalError, match="does not belong to tenant"):
        await queue.reject_request(request_id, tenant_id="tenant-2")


async def test_same_tenant_approve_succeeds() -> None:
    queue = HITLQueue(ttl_seconds=300)
    request_id = await queue.enqueue_request(
        intent_text="transfer funds", risk_score=0.7, tenant_id="tenant-1"
    )

    entry = await queue.approve_request(request_id, tenant_id="tenant-1")
    assert entry["status"] == "approved"


# ---------- Redis cache invalidation tests ----------


async def test_redis_cache_invalidated_on_approve() -> None:
    redis_client = MagicMock()
    queue = HITLQueue(ttl_seconds=300, redis_client=redis_client)
    request_id = await queue.enqueue_request(
        intent_text="transfer funds", risk_score=0.7, tenant_id="tenant-1"
    )

    await queue.approve_request(request_id, tenant_id="tenant-1")
    redis_client.delete.assert_called_once_with(f"hitl:{request_id}")


async def test_redis_cache_invalidated_on_reject() -> None:
    redis_client = MagicMock()
    queue = HITLQueue(ttl_seconds=300, redis_client=redis_client)
    request_id = await queue.enqueue_request(
        intent_text="transfer funds", risk_score=0.7, tenant_id="tenant-1"
    )

    await queue.reject_request(request_id, tenant_id="tenant-1")
    redis_client.delete.assert_called_once_with(f"hitl:{request_id}")


async def test_redis_cache_not_invalidated_on_expired() -> None:
    redis_client = MagicMock()
    queue = HITLQueue(ttl_seconds=300, redis_client=redis_client)
    request_id = await queue.enqueue_request(
        intent_text="transfer funds", risk_score=0.7, tenant_id="tenant-1"
    )

    # Force expiration
    with get_db_session() as session:
        model = session.scalar(
            select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == request_id)
        )
        assert model is not None
        model.expires_at = datetime.now(tz=UTC) - timedelta(seconds=1)

    with pytest.raises(ApprovalError):
        await queue.approve_request(request_id, tenant_id="tenant-1")

    redis_client.delete.assert_not_called()
