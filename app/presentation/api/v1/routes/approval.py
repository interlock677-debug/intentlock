from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.application.dto.auth import UserResponse
from app.domain.exceptions.domain_errors import ApprovalError
from app.domain.services.hitl_queue import HITLQueue
from app.infrastructure.logging.audit_logger import log_security_event
from app.infrastructure.observability.metrics import metrics
from app.presentation.api.dependencies.auth import require_hitl_approver

router = APIRouter(prefix="/approval", tags=["Approval"])

_hitl_queue = HITLQueue()

HitLApprover = Annotated[UserResponse, Depends(require_hitl_approver)]


@router.get("/pending")
async def list_pending(current_user: HitLApprover) -> dict[str, object]:
    """List pending approval requests (authorized approvers only)."""
    pending = await _hitl_queue.list_pending_requests()
    return {"pending": pending}


@router.post("/{request_id}/approve")
async def approve_request(
    request: Request,
    request_id: str,
    current_user: HitLApprover,
) -> dict[str, object]:
    """Approve an HITL request (authorized approver only)."""
    correlation_id = getattr(request.state, "correlation_id", "")
    try:
        entry = await _hitl_queue.approve_request(request_id, decided_by=current_user.id)
    except ApprovalError as exc:
        log_security_event(
            "approval_approve_failed",
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    log_security_event(
        "approval_approved",
        correlation_id=correlation_id,
        request_id=request_id,
        user_id=str(current_user.id),
        risk_score=entry.get("risk_score"),
    )
    metrics.increment_hitl_event("approved")
    return {"request_id": request_id, "status": "approved"}


@router.post("/{request_id}/reject")
async def reject_request(
    request: Request,
    request_id: str,
    current_user: HitLApprover,
) -> dict[str, object]:
    """Reject an HITL request (authorized approver only)."""
    correlation_id = getattr(request.state, "correlation_id", "")
    try:
        entry = await _hitl_queue.reject_request(request_id, decided_by=current_user.id)
    except ApprovalError as exc:
        log_security_event(
            "approval_reject_failed",
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    log_security_event(
        "approval_rejected",
        correlation_id=correlation_id,
        request_id=request_id,
        user_id=str(current_user.id),
        risk_score=entry.get("risk_score"),
    )
    metrics.increment_hitl_event("rejected")
    return {"request_id": request_id, "status": "rejected"}
