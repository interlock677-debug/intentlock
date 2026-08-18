import asyncio
from typing import Any

from app.domain.entities.user import User
from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService
from sdk.langchain_adapter import IntentLockLangChainTool


class FakeResponse:
    def __init__(self, response: Any) -> None:
        self._response = response

    def getcode(self) -> int:
        return self._response.status_code

    def read(self) -> bytes:
        return self._response.content

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        return None


async def _create_user(email: str, role: str = "viewer") -> str:
    settings = get_settings()
    session = SessionLocal()
    try:
        repo = SQLAlchemyUserRepository(session)
        user = User(
            id=__import__("uuid").uuid4(),
            email=email,
            hashed_password=BcryptPasswordHasher(rounds=4).hash("Password123!"),
            is_active=True,
            created_at=__import__("datetime").datetime.now(tz=__import__("datetime").UTC),
            role=role,
            tenant_id="test-tenant",
        )
        saved = await repo.save(user)
        token = JWTTokenService(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_access_token_expire_minutes,
            clock_skew_seconds=settings.jwt_clock_skew_seconds,
        ).create_access_token(user_id=saved.id, email=saved.email)
        session.commit()
        return token
    finally:
        session.close()


def test_intent_lock_langchain_tool_allows_valid_call(client, monkeypatch):
    def add_numbers(
        a: int, b: int, user_prompt: str = "Add two numbers", agent_id: str = "agent-000"
    ) -> int:
        return a + b

    token = asyncio.run(
        _create_user("langchain-test@example.com")
    )

    tool = IntentLockLangChainTool(
        add_numbers,
        base_url="http://testserver/api/v1/intent/verify",
        auth_token=token,
    )

    def fake_urlopen(request: Any, timeout: int = 5) -> FakeResponse:
        headers = dict(request.header_items())
        response = client.post(request.get_full_url(), data=request.data, headers=headers)
        return FakeResponse(response)

    monkeypatch.setattr("sdk.langchain_adapter.urlopen", fake_urlopen)

    result = tool(2, 3, user_prompt="Add two numbers and return the result", agent_id="agent-123")

    assert result == 5


def test_intent_lock_langchain_tool_blocks_malicious_action(client, monkeypatch):
    def search(
        query: str, user_prompt: str = "Search records", agent_id: str = "agent-000"
    ) -> str:
        return "results"

    token = asyncio.run(
        _create_user("langchain-block@example.com")
    )

    tool = IntentLockLangChainTool(
        search,
        base_url="http://testserver/api/v1/intent/verify",
        auth_token=token,
    )

    def fake_urlopen(request: Any, timeout: int = 5) -> FakeResponse:
        headers = dict(request.header_items())
        response = client.post(request.get_full_url(), data=request.data, headers=headers)
        return FakeResponse(response)

    monkeypatch.setattr("sdk.langchain_adapter.urlopen", fake_urlopen)

    result = tool(
        "DROP TABLE users;",
        user_prompt="Run a harmful query",
        agent_id="agent-123",
    )

    assert result.startswith("ACTION BLOCKED BY SECURITY POLICY:")
    assert "Destructive SQL detected" in result or "Deny execution of dangerous tools" in result
