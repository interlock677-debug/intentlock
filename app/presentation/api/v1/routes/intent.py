from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.application.interfaces.execution_token_service import ExecutionTokenService
from app.domain.exceptions.domain_errors import ExecutionTokenError
from app.domain.models.intent import AgentActionDAG, IntentProofResponse
from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.infrastructure.config.settings import get_settings
from app.infrastructure.logging.audit_logger import log_verification
from app.presentation.api.dependencies.security import get_execution_token_service

router = APIRouter(prefix="/intent", tags=["Intent"])

_evaluator = IntentEvaluatorService()


class ExecuteRequest(BaseModel):
    execution_token: str


@router.post("/verify", response_model=IntentProofResponse)
async def verify_intent(
    request: Request,
    agent_action: AgentActionDAG,
    execution_token_service: Annotated[ExecutionTokenService, Depends(get_execution_token_service)],
) -> IntentProofResponse:
    correlation_id = getattr(request.state, "correlation_id", "")
    result = _evaluator.evaluate(agent_action)
    if not result.is_valid:
        log_verification(
            agent_id=agent_action.agent_id,
            proposed_tool=agent_action.proposed_tool,
            tool_arguments=agent_action.tool_arguments,
            verification_status="BLOCKED",
            rejection_reason=result.reason,
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.reason)

    settings = get_settings()
    ephemeral_token = execution_token_service.create_execution_token(
        agent_id=agent_action.agent_id,
        tool=agent_action.proposed_tool,
        ttl_seconds=settings.execution_token_ttl_seconds,
    )

    log_verification(
        agent_id=agent_action.agent_id,
        proposed_tool=agent_action.proposed_tool,
        tool_arguments=agent_action.tool_arguments,
        verification_status="PERMITTED",
        rejection_reason="",
        correlation_id=correlation_id,
    )
    return IntentProofResponse(
        is_valid=True,
        confidence_score=result.confidence_score,
        reason=result.reason,
        ephemeral_token=ephemeral_token,
    )


@router.post("/execute")
async def execute_intent(
    request: Request,
    body: ExecuteRequest,
    execution_token_service: Annotated[ExecutionTokenService, Depends(get_execution_token_service)],
) -> dict[str, str]:
    """Execute an action using a verified ephemeral token.

    The token is atomically consumed on first use. Replay attempts are
    rejected. This endpoint enforces single-use semantics.
    """
    correlation_id = getattr(request.state, "correlation_id", "")

    try:
        payload = execution_token_service.verify_execution_token(body.execution_token)
    except ExecutionTokenError as exc:
        log_verification(
            agent_id="unknown",
            proposed_tool="unknown",
            tool_arguments={},
            verification_status="REPLAY_BLOCKED",
            rejection_reason=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    log_verification(
        agent_id=str(payload.get("sub", "")),
        proposed_tool=str(payload.get("tool", "")),
        tool_arguments={},
        verification_status="EXECUTED",
        rejection_reason="",
        correlation_id=correlation_id,
    )
    return {"status": "executed", "agent_id": str(payload.get("sub", ""))}
