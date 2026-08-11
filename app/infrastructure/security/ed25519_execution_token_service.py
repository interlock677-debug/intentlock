import base64
import time
from typing import Any
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives import serialization

from app.application.interfaces.execution_token_service import ExecutionTokenService
from app.application.interfaces.key_manager import KeyManager
from app.application.interfaces.nonce_store import NonceStore
from app.domain.exceptions.domain_errors import ExecutionTokenError


class Ed25519ExecutionTokenService(ExecutionTokenService):
    """Ed25519-signed ephemeral execution tokens with replay protection.

    Tokens are signed with Ed25519 (EdDSA) and include a JTI (nonce) that
    is atomically consumed via the NonceStore to prevent replay attacks.
    """

    def __init__(
        self,
        *,
        key_manager: KeyManager,
        nonce_store: NonceStore,
        clock_skew_seconds: int = 30,
    ) -> None:
        self._key_manager = key_manager
        self._nonce_store = nonce_store
        self._clock_skew_seconds = clock_skew_seconds

    def create_execution_token(
        self,
        *,
        agent_id: str,
        tool: str,
        ttl_seconds: int,
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": agent_id,
            "type": "execution",
            "tool": tool,
            "iat": now,
            "nbf": now,
            "exp": now + ttl_seconds,
            "jti": str(uuid4()),
        }
        return jwt.encode(
            payload,
            self._key_manager.get_signing_key(),
            algorithm="EdDSA",
        )

    def verify_execution_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self._key_manager.get_verification_key(),
                algorithms=["EdDSA"],
                options={
                    "require": ["sub", "type", "tool", "exp", "iat", "jti"],
                    "verify_nbf": True,
                    # exp is checked explicitly below with strict semantics
                    # (no leeway) so that token lifetime is not extended beyond
                    # the configured ``exp``.  Clock-skew leeway is applied only
                    # to ``nbf`` to tolerate issuer/validator time drift.
                    "verify_exp": False,
                },
                leeway=self._clock_skew_seconds,
            )
        except jwt.PyJWTError as exc:
            raise ExecutionTokenError("Invalid or expired execution token.") from exc

        if payload.get("type") != "execution":
            raise ExecutionTokenError("Invalid token type.")

        nonce = str(payload.get("jti", ""))
        if not nonce:
            raise ExecutionTokenError("Missing token nonce.")

        # Strict expiration check — no leeway.  The token's ``exp`` is the
        # authoritative deadline; clock-skew tolerance must not extend a
        # token's lifetime past the instant it was meant to expire.
        if int(payload["exp"]) < int(time.time()):
            raise ExecutionTokenError("Execution token has expired.")

        ttl_seconds = max(int(payload["exp"]) - int(time.time()), 1)
        if not self._nonce_store.consume(nonce, ttl_seconds):
            raise ExecutionTokenError("Token has already been used.")

        return payload

    def get_jwks(self) -> dict[str, Any]:
        public_key = self._key_manager.get_verification_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return {
            "keys": [
                {
                    "kty": "OKP",
                    "kid": "intentlock-ed25519",
                    "crv": "Ed25519",
                    "x": base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii"),
                    "use": "sig",
                    "alg": "EdDSA",
                }
            ]
        }
