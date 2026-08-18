from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.domain.exceptions.domain_errors import ApprovalError
from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.persistence.models.approval_request_model import ApprovalRequestModel


class HITLQueue:
    """Human-in-the-loop approval queue.

    Supports non-blocking approval workflows with expiration, timeout
    handling, and audit trail. Requests are durably persisted in the
    database so they survive application restarts and are shared across
    application instances. Entries expire after a configurable TTL.
    """

    def __init__(self, *, ttl_seconds: int = 300, redis_client: Any | None = None) -> None:
        self._ttl_seconds = ttl_seconds
        self._redis_client = redis_client

    async def enqueue_request(
        self,
        *,
        request_id: str | None = None,
        intent_text: str = "",
        risk_score: float = 0.0,
        tenant_id: str | None = None,
        user_id: UUID | None = None,
    ) -> str:
        request_key = request_id or str(uuid4())
        now = datetime.now(tz=UTC)
        try:
            with get_db_session() as session:
                session.add(
                    ApprovalRequestModel(
                        request_id=request_key,
                        intent_text=intent_text,
                        risk_score=risk_score,
                        status="pending",
                        created_at=now,
                        expires_at=now + timedelta(seconds=self._ttl_seconds),
                        tenant_id=tenant_id,
                        user_id=user_id,
                    )
                )
        except IntegrityError as exc:
            raise ApprovalError(f"Approval request {request_key} already exists") from exc

        # Best-effort cache write for fast lookups; the database is the source of truth.
        if self._redis_client is not None:
            with contextlib.suppress(Exception):
                self._redis_client.set(
                    f"hitl:{request_key}",
                    str({"request_id": request_key, "status": "pending", "tenant_id": tenant_id}),
                    ex=self._ttl_seconds,
                )
        return request_key

    async def approve_request(
        self,
        request_id: str,
        *,
        decided_by: UUID | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        return await self._decide(
            request_id, "approved", decided_by=decided_by, tenant_id=tenant_id
        )

    async def reject_request(
        self,
        request_id: str,
        *,
        decided_by: UUID | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        return await self._decide(
            request_id, "rejected", decided_by=decided_by, tenant_id=tenant_id
        )

    async def list_pending_requests(
        self, *, tenant_id: str | None = None
    ) -> list[dict[str, object]]:
        now = datetime.now(tz=UTC)
        with get_db_session() as session:
            stmt = (
                select(ApprovalRequestModel)
                .where(ApprovalRequestModel.status == "pending")
                .order_by(ApprovalRequestModel.created_at)
            )
            if tenant_id is not None:
                stmt = stmt.where(ApprovalRequestModel.tenant_id == tenant_id)
            pending = session.scalars(stmt).all()
            result: list[dict[str, object]] = []
            for model in pending:
                if self._as_utc(model.expires_at) <= now:
                    model.status = "expired"
                    model.decided_at = now
                else:
                    result.append(self._to_dict(model))
            return result

    def reset(self) -> None:
        with get_db_session() as session:
            session.execute(delete(ApprovalRequestModel))

    async def _decide(
        self,
        request_id: str,
        decision: str,
        *,
        decided_by: UUID | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        now = datetime.now(tz=UTC)
        with get_db_session() as session:
            model = session.scalar(
                select(ApprovalRequestModel).where(ApprovalRequestModel.request_id == request_id)
            )
            if model is None:
                raise ApprovalError(f"Approval request {request_id} not found")

            if self._as_utc(model.expires_at) <= now:
                model.status = "expired"
                model.decided_at = now
                result = self._to_dict(model)
                expired = True
            elif model.status != "pending":
                raise ApprovalError(f"Approval request {request_id} has already been resolved")
            else:
                if tenant_id is not None and model.tenant_id != tenant_id:
                    raise ApprovalError(
                        f"Approval request {request_id} does not belong to tenant {tenant_id}"
                    )
                model.status = decision
                model.decided_at = now
                model.decided_by = decided_by
                result = self._to_dict(model)
                expired = False

        if expired:
            raise ApprovalError(f"Approval request {request_id} has expired")

        if self._redis_client is not None:
            with contextlib.suppress(Exception):
                self._redis_client.delete(f"hitl:{request_id}")

        return result

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        """Normalize a possibly-naive datetime to an aware UTC datetime.

        SQLite stores ``DateTime(timezone=True)`` columns as naive datetimes,
        so values read back from the database must be re-attached to UTC before
        comparison with aware ``datetime.now(tz=UTC)`` values.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    def _to_dict(self, model: ApprovalRequestModel) -> dict[str, object]:
        return {
            "request_id": model.request_id,
            "intent_text": model.intent_text,
            "risk_score": model.risk_score,
            "status": model.status,
            "created_at": self._as_utc(model.created_at).isoformat(),
            "expires_at": self._as_utc(model.expires_at).isoformat(),
            "decided_at": self._as_utc(model.decided_at).isoformat() if model.decided_at else None,
            "decided_by": str(model.decided_by) if model.decided_by else None,
            "tenant_id": model.tenant_id,
            "user_id": str(model.user_id) if model.user_id else None,
        }
