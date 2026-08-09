import pytest

from app.application.dto.auth import LoginRequest, RegisterRequest
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.register_user import RegisterUserUseCase
from app.domain.exceptions.domain_errors import AuthenticationError
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService
from sqlalchemy.orm import Session


@pytest.fixture
def auth_stack(db_session: Session) -> tuple[RegisterUserUseCase, AuthenticateUserUseCase]:
    repository = SQLAlchemyUserRepository(db_session)
    hasher = BcryptPasswordHasher(rounds=4)
    tokens = JWTTokenService(
        secret_key="test-secret-key-that-is-at-least-32-characters-long",
        algorithm="HS256",
        expire_minutes=30,
    )
    return (
        RegisterUserUseCase(repository, hasher, tokens),
        AuthenticateUserUseCase(repository, hasher, tokens),
    )


@pytest.mark.asyncio
async def test_authenticate_user_success(
    auth_stack: tuple[RegisterUserUseCase, AuthenticateUserUseCase],
    valid_password: str,
) -> None:
    register, authenticate = auth_stack
    await register.execute(RegisterRequest(email="user@example.com", password=valid_password))

    result = await authenticate.execute(
        LoginRequest(email="user@example.com", password=valid_password),
    )
    assert result.access_token
    assert result.user.email == "user@example.com"


@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(
    auth_stack: tuple[RegisterUserUseCase, AuthenticateUserUseCase],
    valid_password: str,
) -> None:
    register, authenticate = auth_stack
    await register.execute(RegisterRequest(email="user@example.com", password=valid_password))

    with pytest.raises(AuthenticationError):
        await authenticate.execute(
            LoginRequest(email="user@example.com", password="WrongPass1!"),
        )
