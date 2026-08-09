from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.persistence.models.user_model import UserModel


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy adapter for UserRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        model = self._session.scalar(stmt)
        return self._to_entity(model) if model else None

    async def save(self, user: User) -> User:
        model = self._session.get(UserModel, user.id)
        if model is None:
            model = UserModel(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
                is_active=user.is_active,
                created_at=user.created_at,
            )
            self._session.add(model)
        else:
            model.email = user.email
            model.hashed_password = user.hashed_password
            model.is_active = user.is_active

        self._session.flush()
        return self._to_entity(model)

    async def exists_by_email(self, email: str) -> bool:
        stmt = select(UserModel.id).where(UserModel.email == email)
        return self._session.scalar(stmt) is not None

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            is_active=model.is_active,
            created_at=model.created_at,
        )
