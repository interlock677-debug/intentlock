from uuid import uuid4

import pytest

from app.domain.exceptions.domain_errors import AuthenticationError
from app.infrastructure.security.jwt_token_service import JWTTokenService


@pytest.fixture
def token_service() -> JWTTokenService:
    return JWTTokenService(
        secret_key="test-secret-key-that-is-at-least-32-characters-long",  # noqa: S106
        algorithm="HS256",
        expire_minutes=30,
    )


def test_create_and_decode_access_token(token_service: JWTTokenService) -> None:
    user_id = uuid4()
    token = token_service.create_access_token(user_id=user_id, email="user@example.com")
    payload = token_service.decode_access_token(token)
    assert payload.sub == user_id
    assert payload.email == "user@example.com"


def test_decode_rejects_invalid_token(token_service: JWTTokenService) -> None:
    with pytest.raises(AuthenticationError):
        token_service.decode_access_token("invalid.token.value")
