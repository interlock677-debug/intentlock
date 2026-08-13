import base64
import json
import time
from typing import Any
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives import serialization

from app.application.interfaces.execution_token_service import ExecutionTokenService
from app.application.interfaces.key_manager import KeyManager
from app.application.interfaces.nonce_store import NonceStore
from app.domain.exceptions.domain_errors import ExecutionTokenError


def _b64url_encode(data: bytes) -> str:
    """Base64url-encode without padding (RFC 7515)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class Ed25519ExecutionTokenService(ExecutionTokenService):
    """Ed25519-signed ephemeral execution tokens with replay protection.

    Tokens are signed with Ed25519 (EdDSA) and include a JTI (nonce) that
    is atomically consumed via the NonceStore to prevent replay attacks.

    Key rotation support:
        - Each token carries a ``kid`` header identifying the signing key.
        - Verification selects the correct key from the KeyManager by
          ``kid``.  Tokens without ``kid`` fall back to the active key
          (backward compatibility).
        - JWKS returns all currently valid keys (active + previous) so
          clients can verify tokens signed with any still-valid key.
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
        key_id = self._key_manager.active_key_id
        header = {"alg": "EdDSA", "typ": "JWT", "kid": key_id}
        payload = {
            "sub": agent_id,
            "type": "execution",
            "tool": tool,
            "iat": now,
            "nbf": now,
            "exp": now + ttl_seconds,
            "jti": str(uuid4()),
        }

        header_segment = _b64url_encode(
            json.dumps(header, separators=(",", ":")).encode("ascii")
        )
        payload_segment = _b64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("ascii")
        )
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")

        signature = self._key_manager.sign(signing_input, key_id)
        signature_segment = _b64url_encode(signature)

        return f"{header_segment}.{payload_segment}.{signature_segment}"

    def verify_execution_token(self, token: str) -> dict[str, Any]:
        # Extract key ID from the header without verifying the signature.
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise ExecutionTokenError("Invalid or expired execution token.") from None

        kid = header.get("kid")

        # Select the verification key based on the key ID.
        try:
            if kid is not None:
                verify_key = self._key_manager.get_verification_key(kid)
            else:
                verify_key = self._key_manager.get_verification_key()
        except KeyError:
            raise ExecutionTokenError("Unknown key ID.") from None

        # Verify the signature and decode the payload.
        try:
            payload = jwt.decode(
                token,
                verify_key,
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
        keys: list[dict[str, Any]] = []
        for kid in self._key_manager.get_key_ids():
            public_key = self._key_manager.get_verification_key(kid)
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            keys.append(
                {
                    "kty": "OKP",
                    "kid": kid,
                    "crv": "Ed25519",
                    "x": base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii"),
                    "use": "sig",
                    "alg": "EdDSA",
                }
            )
        return {"keys": keys}
