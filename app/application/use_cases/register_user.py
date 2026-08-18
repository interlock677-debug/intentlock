from datetime import UTC, datetime
from uuid import uuid4

from app.application.dto.auth import AuthResponse, RegisterRequest, UserResponse
from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.token_service import TokenService
from app.domain.entities.user import User
from app.domain.exceptions.domain_errors import DuplicateEmailError
from app.domain.repositories.user_repository import UserRepository
from app.domain.value_objects.email_address import EmailAddress


class RegisterUserUseCase:
    """Register a new user with hashed credentials."""

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service

    async def execute(self, request: RegisterRequest) -> AuthResponse:
        email = str(EmailAddress(str(request.email)))

        if await self._user_repository.exists_by_email(email):
            raise DuplicateEmailError(f"Email already registered: {email}")

        tenant_id = getattr(request, "tenant_id", None)
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=self._password_hasher.hash(request.password),
            is_active=True,
            created_at=datetime.now(tz=UTC),
            role="viewer",
            tenant_id=tenant_id,
        )
        saved_user = await self._user_repository.save(user)

        access_token = self._token_service.create_access_token(
            user_id=saved_user.id,
            email=saved_user.email,
        )
        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                id=saved_user.id,
                email=saved_user.email,
                is_active=saved_user.is_active,
                role=saved_user.role,
                tenant_id=saved_user.tenant_id,
            ),
        )
