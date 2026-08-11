from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from app.application.interfaces.token_service import TokenPayload, TokenService
from app.domain.exceptions.domain_errors import AuthenticationError


class JWTTokenService(TokenService):
    """PyJWT adapter for TokenService port.

    Supports JTI (JWT ID) for replay detection, nbf (not-before) claim,
    and configurable clock-skew tolerance.
    """

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        expire_minutes: int,
        clock_skew_seconds: int = 30,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes
        self._clock_skew_seconds = clock_skew_seconds

    def create_access_token(self, *, user_id: UUID, email: str) -> str:
        now = datetime.now(tz=UTC)
        payload = {
            "sub": str(user_id),
            "email": email,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
            "jti": str(uuid4()),
            "type": "access",
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={
                    "require": ["sub", "email", "exp", "iat", "jti"],
                    "verify_nbf": True,
                },
                leeway=self._clock_skew_seconds,
            )
        except InvalidTokenError as exc:
            raise AuthenticationError("Invalid or expired access token.") from exc

        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type.")

        return TokenPayload(
            sub=UUID(str(payload["sub"])),
            email=str(payload["email"]),
            jti=str(payload["jti"]),
        )
