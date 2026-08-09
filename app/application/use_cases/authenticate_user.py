from app.application.dto.auth import AuthResponse, LoginRequest, UserResponse
from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.token_service import TokenService
from app.domain.exceptions.domain_errors import AuthenticationError, InactiveUserError
from app.domain.repositories.user_repository import UserRepository
from app.domain.value_objects.email_address import EmailAddress


class AuthenticateUserUseCase:
    """Authenticate a user and issue an access token."""

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service

    async def execute(self, request: LoginRequest) -> AuthResponse:
        email = str(EmailAddress(str(request.email)))
        user = await self._user_repository.get_by_email(email)

        if user is None or not self._password_hasher.verify(request.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise InactiveUserError("User account is inactive.")

        access_token = self._token_service.create_access_token(
            user_id=user.id,
            email=user.email,
        )
        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
            ),
        )
