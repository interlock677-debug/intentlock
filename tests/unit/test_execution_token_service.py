import time

import jwt
import pytest

from app.domain.exceptions.domain_errors import ExecutionTokenError
from app.infrastructure.security.ed25519_execution_token_service import Ed25519ExecutionTokenService
from app.infrastructure.security.env_key_manager import EnvKeyManager
from app.infrastructure.security.memory_nonce_store import MemoryNonceStore


@pytest.fixture
def token_service() -> Ed25519ExecutionTokenService:
    key_manager = EnvKeyManager(jwt_secret="test-secret-key-that-is-at-least-32-characters-long")
    nonce_store = MemoryNonceStore()
    return Ed25519ExecutionTokenService(
        key_manager=key_manager,
        nonce_store=nonce_store,
        clock_skew_seconds=30,
    )


def test_create_and_verify(token_service: Ed25519ExecutionTokenService) -> None:
    token = token_service.create_execution_token(
        agent_id="agent-123", tool="transfer_funds", ttl_seconds=1
    )
    payload = token_service.verify_execution_token(token)
    assert payload["sub"] == "agent-123"
    assert payload["tool"] == "transfer_funds"
    assert payload["type"] == "execution"
    assert "jti" in payload


def test_replay_rejected(token_service: Ed25519ExecutionTokenService) -> None:
    token = token_service.create_execution_token(
        agent_id="agent-123", tool="transfer_funds", ttl_seconds=1
    )
    assert token_service.verify_execution_token(token) is not None
    with pytest.raises(ExecutionTokenError):
        token_service.verify_execution_token(token)


def test_expired_token_rejected(token_service: Ed25519ExecutionTokenService) -> None:
    # Construct a token with ``exp`` explicitly in the past so the test
    # is deterministic and does not rely on wall-clock timing granularity.
    # The token is signed with the *same* key manager as ``token_service``
    # so that signature verification passes and the expiration check is
    # the sole reason for rejection.
    key_manager = token_service._key_manager
    now = int(time.time())
    payload = {
        "sub": "agent-123",
        "type": "execution",
        "tool": "transfer_funds",
        "iat": now - 60,
        "nbf": now - 60,
        "exp": now - 30,
        "jti": "expired-nonce",
    }
    token = jwt.encode(payload, key_manager.get_signing_key(), algorithm="EdDSA")
    with pytest.raises(ExecutionTokenError):
        token_service.verify_execution_token(token)


def test_malformed_token_rejected(token_service: Ed25519ExecutionTokenService) -> None:
    with pytest.raises(ExecutionTokenError):
        token_service.verify_execution_token("not-a-valid-token")


def test_invalid_signature_rejected(token_service: Ed25519ExecutionTokenService) -> None:
    token = token_service.create_execution_token(
        agent_id="agent-123", tool="transfer_funds", ttl_seconds=1
    )
    parts = token.split(".")
    parts[2] = "tampered"
    with pytest.raises(ExecutionTokenError):
        token_service.verify_execution_token(".".join(parts))


def test_future_token_rejected(token_service: Ed25519ExecutionTokenService) -> None:
    key_manager = EnvKeyManager(jwt_secret="test-secret-key-that-is-at-least-32-characters-long")
    now = int(time.time())
    payload = {
        "sub": "agent-123",
        "type": "execution",
        "tool": "transfer_funds",
        "iat": now + 100,
        "nbf": now + 100,
        "exp": now + 101,
        "jti": "future-nonce",
    }
    token = jwt.encode(payload, key_manager.get_signing_key(), algorithm="EdDSA")
    with pytest.raises(ExecutionTokenError):
        token_service.verify_execution_token(token)


def test_missing_jti_rejected(token_service: Ed25519ExecutionTokenService) -> None:
    key_manager = EnvKeyManager(jwt_secret="test-secret-key-that-is-at-least-32-characters-long")
    now = int(time.time())
    payload = {
        "sub": "agent-123",
        "type": "execution",
        "tool": "transfer_funds",
        "iat": now,
        "nbf": now,
        "exp": now + 1,
    }
    token = jwt.encode(payload, key_manager.get_signing_key(), algorithm="EdDSA")
    with pytest.raises(ExecutionTokenError):
        token_service.verify_execution_token(token)


def test_wrong_token_type_rejected(token_service: Ed25519ExecutionTokenService) -> None:
    key_manager = EnvKeyManager(jwt_secret="test-secret-key-that-is-at-least-32-characters-long")
    now = int(time.time())
    payload = {
        "sub": "agent-123",
        "type": "access",
        "tool": "transfer_funds",
        "iat": now,
        "nbf": now,
        "exp": now + 1,
        "jti": "wrong-type-nonce",
    }
    token = jwt.encode(payload, key_manager.get_signing_key(), algorithm="EdDSA")
    with pytest.raises(ExecutionTokenError):
        token_service.verify_execution_token(token)


def test_jwks_contains_public_key(token_service: Ed25519ExecutionTokenService) -> None:
    jwks = token_service.get_jwks()
    assert "keys" in jwks
    assert len(jwks["keys"]) == 1
    key = jwks["keys"][0]
    assert key["kty"] == "OKP"
    assert key["crv"] == "Ed25519"
    assert key["alg"] == "EdDSA"
    assert "x" in key
