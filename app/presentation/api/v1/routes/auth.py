from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.register_user import RegisterUserUseCase
from app.domain.exceptions.domain_errors import (
    AuthenticationError,
    DuplicateEmailError,
    InactiveUserError,
)
from app.presentation.api.dependencies.auth import (
    CurrentUser,
    get_authenticate_user_use_case,
    get_register_user_use_case,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    use_case: Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)],
) -> AuthResponse:
    try:
        return await use_case.execute(request)
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    use_case: Annotated[AuthenticateUserUseCase, Depends(get_authenticate_user_use_case)],
) -> AuthResponse:
    try:
        return await use_case.execute(request)
    except (AuthenticationError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return current_user
