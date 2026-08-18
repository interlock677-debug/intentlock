from fastapi import APIRouter, HTTPException, status

from app.infrastructure.observability.metrics import metrics
from app.presentation.api.dependencies.auth import CurrentUser

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/security", status_code=status.HTTP_200_OK)
async def get_security_metrics(current_user: CurrentUser) -> dict[str, object]:
    """Return security metrics snapshot (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to view security metrics.",
        )
    return metrics.get_metrics_snapshot()
