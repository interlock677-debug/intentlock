from __future__ import annotations

import contextlib
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.domain.exceptions.domain_errors import ApprovalError


class HITLQueue:
    """Human-in-the-loop approval queue.

    Supports non-blocking approval workflows with expiration, timeout
    handling, and audit trail. Entries expire after a configurable TTL.
    """

    def __init__(self, *, ttl_seconds: int = 300, redis_client: Any | None = None) -> None:
        self._ttl_seconds = ttl_seconds
        self._redis_client = redis_client
        self._pending: OrderedDict[str, dict[str, object]] = OrderedDict()
        self._history: dict[str, dict[str, object]] = {}

    async def enqueue_request(
        self,
        *,
        request_id: str | None = None,
        intent_text: str = "",
        risk_score: float = 0.0,
    ) -> str:
        request_key = request_id or str(uuid4())
        now = datetime.now(tz=UTC)
        entry: dict[str, object] = {
            "request_id": request_key,
            "intent_text": intent_text,
            "risk_score": risk_score,
            "status": "pending",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self._ttl_seconds)).isoformat(),
        }

        if self._redis_client is not None:
            with contextlib.suppress(Exception):
                self._redis_client.set(
                    f"hitl:{request_key}",
                    str(entry),
                    ex=self._ttl_seconds,
                )

        self._pending[request_key] = entry
        return request_key

    async def approve_request(self, request_id: str) -> dict[str, object]:
        return await self._decide(request_id, "approved")

    async def reject_request(self, request_id: str) -> dict[str, object]:
        return await self._decide(request_id, "rejected")

    async def list_pending_requests(self) -> list[dict[str, object]]:
        self._evict_expired()
        return [dict(entry) for entry in self._pending.values()]

    def reset(self) -> None:
        self._pending.clear()
        self._history.clear()

    async def _decide(self, request_id: str, decision: str) -> dict[str, object]:
        self._evict_expired()

        entry = self._pending.get(request_id)
        if entry is None:
            raise ApprovalError(f"Approval request {request_id} not found")

        # Verify the entry has not expired.
        expires_at = datetime.fromisoformat(str(entry["expires_at"]))
        if expires_at <= datetime.now(tz=UTC):
            self._pending.pop(request_id, None)
            entry["status"] = "expired"
            self._history[request_id] = entry
            raise ApprovalError(f"Approval request {request_id} has expired")

        self._pending.pop(request_id, None)
        entry["status"] = decision
        entry["decided_at"] = datetime.now(tz=UTC).isoformat()
        self._history[request_id] = entry
        return entry

    def _evict_expired(self) -> None:
        now = datetime.now(tz=UTC)
        expired = [
            key
            for key, entry in self._pending.items()
            if "expires_at" in entry
            and datetime.fromisoformat(str(entry["expires_at"])) <= now
        ]
        for key in expired:
            entry = self._pending.pop(key)
            entry["status"] = "expired"
            self._history[key] = entry
