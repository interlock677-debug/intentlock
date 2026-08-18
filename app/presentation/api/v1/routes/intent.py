import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.application.interfaces.execution_token_service import ExecutionTokenService
from app.domain.exceptions.domain_errors import (
    ApprovalRequiredError,
    AuthorizationError,
    ExecutionTokenError,
)
from app.domain.models.intent import AgentActionDAG, IntentProofResponse
from app.domain.services.authorization_service import AuthorizationService
from app.domain.services.central_policy_engine import CentralPolicyEngine
from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.domain.value_objects.authorization_context import AuthorizationContext
from app.domain.value_objects.authorization_decision import AuthorizationDecision
from app.infrastructure.config.settings import get_settings
from app.infrastructure.logging.audit_logger import log_verification
from app.infrastructure.observability.metrics import metrics
from app.presentation.api.dependencies.auth import CurrentUser
from app.presentation.api.dependencies.security import get_execution_token_service

router = APIRouter(prefix="/intent", tags=["Intent"])

_evaluator = IntentEvaluatorService()
_authz_service = AuthorizationService()
_policy_engine = CentralPolicyEngine.from_file()


class ExecuteRequest(BaseModel):
    execution_token: str


def _extract_jti(token: str) -> str | None:
    try:
        parts = token.split(".")
        payload = json.loads(__import__("base64").b64decode(parts[1] + "=="))
        return str(payload.get("jti", "")) or None
    except Exception:
        return None


@router.post("/verify", response_model=IntentProofResponse)
async def verify_intent(
    request: Request,
    agent_action: AgentActionDAG,
    current_user: CurrentUser,
    execution_token_service: Annotated[ExecutionTokenService, Depends(get_execution_token_service)],
) -> IntentProofResponse:
    correlation_id = getattr(request.state, "correlation_id", "")

    if (
        current_user.tenant_id
        and agent_action.tenant_id
        and current_user.tenant_id != agent_action.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant mismatch: request tenant does not match user tenant.",
        )

    auth_context = AuthorizationContext(
        user_id=current_user.id,
        agent_id=agent_action.agent_id,
        proposed_tool=agent_action.proposed_tool,
        tenant_id=agent_action.tenant_id,
        action=agent_action.action,
        resource=agent_action.resource or "",
        service_id=agent_action.service_id,
    )
    auth_decision, auth_reason = _authz_service.authorize(auth_context)

    if auth_decision == AuthorizationDecision.DENY:
        metrics.increment_authorization_denial(auth_reason)
        log_verification(
            agent_id=agent_action.agent_id,
            proposed_tool=agent_action.proposed_tool,
            tool_arguments=agent_action.tool_arguments,
            verification_status="AUTH_DENIED",
            rejection_reason=auth_reason,
            correlation_id=correlation_id,
        )
        raise AuthorizationError(auth_reason)

    if auth_decision == AuthorizationDecision.REQUIRE_HITL:
        log_verification(
            agent_id=agent_action.agent_id,
            proposed_tool=agent_action.proposed_tool,
            tool_arguments=agent_action.tool_arguments,
            verification_status="AUTH_REQUIRE_HITL",
            rejection_reason=auth_reason,
            correlation_id=correlation_id,
        )
        raise ApprovalRequiredError(auth_reason)

    policy_result = _policy_engine.evaluate(auth_context)
    if policy_result.effect == AuthorizationDecision.DENY:
        metrics.increment_policy_decision(policy_result.effect.value)
        log_verification(
            agent_id=agent_action.agent_id,
            proposed_tool=agent_action.proposed_tool,
            tool_arguments=agent_action.tool_arguments,
            verification_status="POLICY_DENIED",
            rejection_reason=policy_result.reason,
            correlation_id=correlation_id,
        )
        raise AuthorizationError(policy_result.reason)

    if policy_result.effect == AuthorizationDecision.REQUIRE_HITL:
        metrics.increment_policy_decision(policy_result.effect.value)
        log_verification(
            agent_id=agent_action.agent_id,
            proposed_tool=agent_action.proposed_tool,
            tool_arguments=agent_action.tool_arguments,
            verification_status="POLICY_REQUIRE_HITL",
            rejection_reason=policy_result.reason,
            correlation_id=correlation_id,
        )
        raise ApprovalRequiredError(policy_result.reason)

    result = _evaluator.evaluate(agent_action)
    if not result.is_valid:
        metrics.increment_policy_decision("blocked")
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
        subject=str(current_user.id),
    )
    metrics.increment_execution_tokens_issued()
    token_jti = _extract_jti(ephemeral_token)

    log_verification(
        agent_id=agent_action.agent_id,
        proposed_tool=agent_action.proposed_tool,
        tool_arguments=agent_action.tool_arguments,
        verification_status="PERMITTED",
        rejection_reason="",
        correlation_id=correlation_id,
        jti=token_jti,
    )
    return IntentProofResponse(
        is_valid=True,
        confidence_score=result.confidence_score,
        reason=result.reason,
        ephemeral_token=ephemeral_token,
        requires_hitl=False,
    )


@router.post("/execute")
async def execute_intent(
    request: Request,
    body: ExecuteRequest,
    current_user: CurrentUser,
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
        metrics.increment_execution_tokens_replayed()
        token_jti = _extract_jti(body.execution_token)
        log_verification(
            agent_id="unknown",
            proposed_tool="unknown",
            tool_arguments={},
            verification_status="REPLAY_BLOCKED",
            rejection_reason=str(exc),
            correlation_id=correlation_id,
            jti=token_jti,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    token_subject = str(payload.get("sub", ""))
    if token_subject != str(current_user.id):
        log_verification(
            agent_id=str(payload.get("agent_id", payload.get("sub", ""))),
            proposed_tool=str(payload.get("tool", "")),
            tool_arguments={},
            verification_status="SUBJECT_MISMATCH",
            rejection_reason="Token subject does not match authenticated user.",
            correlation_id=correlation_id,
            jti=str(payload.get("jti", "")) or None,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token subject does not match authenticated user.",
        )

    log_verification(
        agent_id=str(payload.get("agent_id", payload.get("sub", ""))),
        proposed_tool=str(payload.get("tool", "")),
        tool_arguments={},
        verification_status="EXECUTED",
        rejection_reason="",
        correlation_id=correlation_id,
        jti=str(payload.get("jti", "")) or None,
    )
    metrics.increment_execution_tokens_consumed()
    return {"status": "executed", "agent_id": str(payload.get("agent_id", payload.get("sub", "")))}
