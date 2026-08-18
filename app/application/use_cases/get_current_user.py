from uuid import UUID

from app.application.dto.auth import UserResponse
from app.domain.exceptions.domain_errors import UserNotFoundError
from app.domain.repositories.user_repository import UserRepository


class GetCurrentUserUseCase:
    """Retrieve the authenticated user's profile."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def execute(self, user_id: UUID) -> UserResponse:
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")

        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            role=user.role,
            tenant_id=user.tenant_id,
        )
