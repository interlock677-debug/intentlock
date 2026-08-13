import time
from pathlib import Path
from uuid import uuid4

import jwt
import pytest

from app.domain.exceptions.domain_errors import AuthenticationError, ExecutionTokenError
from app.infrastructure.security.ed25519_execution_token_service import Ed25519ExecutionTokenService
from app.infrastructure.security.env_key_manager import EnvKeyManager
from app.infrastructure.security.jwt_token_service import JWTTokenService
from app.infrastructure.security.memory_nonce_store import MemoryNonceStore


def test_env_key_manager(tmp_path: Path) -> None:
    # In-memory creation
    km1 = EnvKeyManager(jwt_secret="secret123", execution_key_path=None)
    assert km1.get_secret("jwt_secret") == "secret123"

    with pytest.raises(KeyError):
        km1.get_secret("invalid_secret_name")

    sk1 = km1.get_signing_key()
    vk1 = km1.get_verification_key()
    assert sk1 is not None and vk1 is not None

    # File path persistence creation & reloading
    key_file = tmp_path / "keys" / "ed25519.pem"
    km2 = EnvKeyManager(jwt_secret="secret123", execution_key_path=str(key_file))
    sk2 = km2.get_signing_key()
    assert key_file.exists()

    # Reload from existing key file
    km3 = EnvKeyManager(jwt_secret="secret123", execution_key_path=str(key_file))
    sk3 = km3.get_signing_key()
    assert sk3.private_bytes_raw() == sk2.private_bytes_raw()


def test_jwt_token_service() -> None:
    svc = JWTTokenService(
        secret_key="my-secret-key-32-chars-at-least!",
        algorithm="HS256",
        expire_minutes=15,
    )
    u_id = uuid4()
    token = svc.create_access_token(user_id=u_id, email="test@example.com")

    payload = svc.decode_access_token(token)
    assert payload.sub == u_id
    assert payload.email == "test@example.com"

    # Invalid token string
    with pytest.raises(AuthenticationError):
        svc.decode_access_token("invalid.jwt.token")

    # Wrong token type
    bad_type_token = jwt.encode(
        {
            "sub": str(u_id),
            "email": "a@b.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 100,
            "jti": "1",
            "type": "refresh",
        },
        "my-secret-key-32-chars-at-least!",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError) as exc_info:
        svc.decode_access_token(bad_type_token)
    assert "Invalid token type" in str(exc_info.value)


def test_ed25519_execution_token_service() -> None:
    km = EnvKeyManager(jwt_secret="secret123", execution_key_path=None)
    nonce_store = MemoryNonceStore()
    svc = Ed25519ExecutionTokenService(
        key_manager=km,
        nonce_store=nonce_store,
        clock_skew_seconds=5,
    )

    # Valid token creation & verification
    token = svc.create_execution_token(
        agent_id="agent-007",
        tool="financial_transfer",
        ttl_seconds=10,
    )
    verified = svc.verify_execution_token(token)
    assert verified["sub"] == "agent-007"
    assert verified["tool"] == "financial_transfer"

    # Replay protection: reusing token fails
    with pytest.raises(ExecutionTokenError) as exc_replay:
        svc.verify_execution_token(token)
    assert "already been used" in str(exc_replay.value)

    # Invalid token string
    with pytest.raises(ExecutionTokenError):
        svc.verify_execution_token("invalid.token.here")

    # Invalid token type
    sk = km.get_signing_key()
    now = int(time.time())
    bad_type_token = jwt.encode(
        {
            "sub": "agent",
            "tool": "tool",
            "iat": now,
            "nbf": now,
            "exp": now + 10,
            "jti": str(uuid4()),
            "type": "wrong_type",
        },
        sk,
        algorithm="EdDSA",
    )
    with pytest.raises(ExecutionTokenError) as exc_type:
        svc.verify_execution_token(bad_type_token)
    assert "Invalid token type" in str(exc_type.value)

    # Expired token
    exp_token = jwt.encode(
        {
            "sub": "agent",
            "tool": "tool",
            "iat": now - 20,
            "nbf": now - 20,
            "exp": now - 10,
            "jti": str(uuid4()),
            "type": "execution",
        },
        sk,
        algorithm="EdDSA",
    )
    with pytest.raises(ExecutionTokenError) as exc_exp:
        svc.verify_execution_token(exp_token)
    assert "expired" in str(exc_exp.value)

    # JWKS export
    jwks = svc.get_jwks()
    assert "keys" in jwks
    assert jwks["keys"][0]["alg"] == "EdDSA"

    # Missing JTI / Nonce
    no_nonce_token = jwt.encode(
        {
            "sub": "agent",
            "tool": "tool",
            "iat": now,
            "nbf": now,
            "exp": now + 10,
            "jti": "",
            "type": "execution",
        },
        sk,
        algorithm="EdDSA",
    )
    with pytest.raises(ExecutionTokenError) as exc_no_jti:
        svc.verify_execution_token(no_nonce_token)
    assert "Missing token nonce" in str(exc_no_jti.value)


def test_memory_nonce_store_limits_and_eviction() -> None:
    store = MemoryNonceStore(max_entries=2, ttl_seconds=1)

    assert store.consume("n1", ttl_seconds=1) is True
    assert store.consume("n1", ttl_seconds=1) is False  # Duplicate
    assert store.is_consumed("n1") is True
    assert store.is_consumed("n_absent") is False

    # Overflow eviction (max_entries=2)
    assert store.consume("n2", ttl_seconds=1) is True
    assert store.consume("n3", ttl_seconds=1) is True  # n1 evicted due to overflow
    assert store.is_consumed("n1") is False

    # Expiration eviction
    time.sleep(1.1)
    assert store.is_consumed("n2") is False
