from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, HTTPException, status

from app.domain.models.intent import AgentActionDAG, IntentProofResponse
from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.infrastructure.config.settings import get_settings
from app.infrastructure.logging.audit_logger import log_verification

router = APIRouter(prefix="/intent", tags=["Intent"])


@router.post("/verify", response_model=IntentProofResponse)
async def verify_intent(agent_action: AgentActionDAG) -> IntentProofResponse:
    evaluator = IntentEvaluatorService()
    result = evaluator.evaluate(agent_action)
    if not result.is_valid:
        log_verification(
            agent_id=agent_action.agent_id,
            proposed_tool=agent_action.proposed_tool,
            tool_arguments=agent_action.tool_arguments,
            verification_status="BLOCKED",
            rejection_reason=result.reason,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.reason)

    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    token_payload = {
        "sub": agent_action.agent_id,
        "type": "execution",
        "tool": agent_action.proposed_tool,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=1)).timestamp()),
    }
    ephemeral_token = jwt.encode(token_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    log_verification(
        agent_id=agent_action.agent_id,
        proposed_tool=agent_action.proposed_tool,
        tool_arguments=agent_action.tool_arguments,
        verification_status="PERMITTED",
        rejection_reason="",
    )
    return IntentProofResponse(
        is_valid=True,
        confidence_score=result.confidence_score,
        reason=result.reason,
        ephemeral_token=ephemeral_token,
    )
