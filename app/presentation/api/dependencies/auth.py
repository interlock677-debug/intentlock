from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.dto.auth import UserResponse
from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.token_service import TokenService
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.get_current_user import GetCurrentUserUseCase
from app.application.use_cases.register_user import RegisterUserUseCase
from app.domain.exceptions.domain_errors import AuthenticationError, UserNotFoundError
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings() -> Settings:
    return get_settings()


def _get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(_get_session)]


def get_user_repository(session: DbSession) -> UserRepository:
    return SQLAlchemyUserRepository(session)


def get_password_hasher(settings: Annotated[Settings, Depends(get_app_settings)]) -> PasswordHasher:
    return BcryptPasswordHasher(rounds=settings.bcrypt_rounds)


def get_token_service(settings: Annotated[Settings, Depends(get_app_settings)]) -> TokenService:
    return JWTTokenService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_access_token_expire_minutes,
    )


def get_register_user_use_case(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> RegisterUserUseCase:
    return RegisterUserUseCase(user_repository, password_hasher, token_service)


def get_authenticate_user_use_case(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(user_repository, password_hasher, token_service)


def get_current_user_use_case(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> GetCurrentUserUseCase:
    return GetCurrentUserUseCase(user_repository)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = token_service.decode_access_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return payload.sub


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]


async def get_current_user(
    user_id: CurrentUserId,
    use_case: Annotated[GetCurrentUserUseCase, Depends(get_current_user_use_case)],
) -> UserResponse:
    try:
        return await use_case.execute(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
