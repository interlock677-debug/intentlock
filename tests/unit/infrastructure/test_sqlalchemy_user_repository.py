import pytest

from app.domain.entities.user import User
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher


@pytest.fixture
def session() -> SessionLocal:
    session = SessionLocal()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_sqlalchemy_user_repository_get_by_tenant_returns_users(
    session: SessionLocal,
) -> None:
    repo = SQLAlchemyUserRepository(session)
    user = User(
        id=__import__("uuid").uuid4(),
        email="tenant-user@example.com",
        hashed_password=BcryptPasswordHasher(rounds=4).hash("Password123!"),
        is_active=True,
        created_at=__import__("datetime").datetime.now(tz=__import__("datetime").UTC),
        role="viewer",
        tenant_id="tenant-abc",
    )
    await repo.save(user)
    session.commit()

    users = await repo.get_by_tenant("tenant-abc")
    assert len(users) == 1
    assert users[0].email == "tenant-user@example.com"


@pytest.mark.asyncio
async def test_sqlalchemy_user_repository_get_by_tenant_empty(session: SessionLocal) -> None:
    repo = SQLAlchemyUserRepository(session)
    users = await repo.get_by_tenant("nonexistent-tenant")
    assert users == []
