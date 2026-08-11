from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.application.interfaces.execution_token_service import ExecutionTokenService
from app.presentation.api.dependencies.security import get_execution_token_service

router = APIRouter(tags=["Discovery"])


@router.get("/.well-known/jwks.json")
async def jwks(
    execution_token_service: Annotated[ExecutionTokenService, Depends(get_execution_token_service)],
) -> dict[str, Any]:
    """Return the public JWKS for execution token verification."""
    return execution_token_service.get_jwks()
