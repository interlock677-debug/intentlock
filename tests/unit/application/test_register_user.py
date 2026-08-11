import pytest
from sqlalchemy.orm import Session

from app.application.dto.auth import RegisterRequest
from app.application.use_cases.register_user import RegisterUserUseCase
from app.domain.exceptions.domain_errors import DuplicateEmailError
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService


@pytest.fixture
def register_use_case(db_session: Session) -> RegisterUserUseCase:
    return RegisterUserUseCase(
        user_repository=SQLAlchemyUserRepository(db_session),
        password_hasher=BcryptPasswordHasher(rounds=4),
        token_service=JWTTokenService(
            secret_key="test-secret-key-that-is-at-least-32-characters-long",
            algorithm="HS256",
            expire_minutes=30,
        ),
    )


@pytest.mark.asyncio
async def test_register_user_success(
    register_use_case: RegisterUserUseCase,
    valid_password: str,
) -> None:
    result = await register_use_case.execute(
        RegisterRequest(email="user@example.com", password=valid_password),
    )
    assert result.access_token
    assert result.user.email == "user@example.com"
    assert result.user.is_active is True


@pytest.mark.asyncio
async def test_register_user_duplicate_email(
    register_use_case: RegisterUserUseCase,
    valid_password: str,
) -> None:
    request = RegisterRequest(email="user@example.com", password=valid_password)
    await register_use_case.execute(request)

    with pytest.raises(DuplicateEmailError):
        await register_use_case.execute(request)
