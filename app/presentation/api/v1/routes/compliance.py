from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.application.use_cases.export_compliance_evidence import ExportComplianceEvidenceUseCase
from app.infrastructure.config.settings import Settings, get_settings
from app.presentation.api.dependencies.auth import CurrentUser

router = APIRouter(prefix="/compliance", tags=["Compliance"])


@router.get("/evidence", status_code=status.HTTP_200_OK)
async def export_compliance_evidence(
    current_user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    """Export compliance evidence package (admin only).

    Returns a tamper-evident JSON package containing access-control evidence,
    policy history, HITL approval history, and authorization decision logs.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to export compliance evidence.",
        )

    use_case = ExportComplianceEvidenceUseCase(secret_key=settings.compliance_secret_key)
    evidence = use_case.execute()

    filename = f"compliance-evidence-{evidence.get('package_id', 'export')}.json"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return JSONResponse(content=evidence, headers=headers)
