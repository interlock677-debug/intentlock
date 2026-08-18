from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuthorizationContext:
    """Immutable bundle of identities for an authorization decision."""

    user_id: UUID
    agent_id: str
    proposed_tool: str
    tenant_id: str | None = None
    action: str = "execute"
    resource: str = ""
    service_id: str | None = None
    authorized_at: datetime | None = field(default=None, kw_only=True)
