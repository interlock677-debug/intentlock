from abc import ABC, abstractmethod
from typing import Any


class ExecutionTokenService(ABC):
    """Port for ephemeral execution token creation and validation."""

    @abstractmethod
    def create_execution_token(
        self,
        *,
        agent_id: str,
        tool: str,
        ttl_seconds: int,
    ) -> str: ...

    @abstractmethod
    def verify_execution_token(self, token: str) -> dict[str, Any]:
        """Verify an execution token and consume its nonce.

        Returns the token payload if valid, raises ExecutionTokenError
        if the token is invalid, expired, or replayed.
        """

    @abstractmethod
    def get_jwks(self) -> dict[str, Any]:
        """Return the public JWKS for execution token verification."""
