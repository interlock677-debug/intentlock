from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AgentActionDAG(BaseModel):
    user_prompt: str
    agent_id: str
    reasoning_step: str
    proposed_tool: str
    tool_arguments: dict[str, Any]
    tenant_id: str | None = None
    service_id: str | None = None
    action: str = "execute"
    resource: str = ""


class IntentProofResponse(BaseModel):
    is_valid: bool
    confidence_score: float
    reason: str
    ephemeral_token: str | None = None
    requires_hitl: bool = False
