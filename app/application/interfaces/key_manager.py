from abc import ABC, abstractmethod
from typing import Any


class KeyManager(ABC):
    """Port for cryptographic key storage and retrieval.

    Production implementations should delegate to external key-management
    systems (AWS KMS, Google Cloud KMS, HashiCorp Vault). The application
    must never log or expose private key material.
    """

    @abstractmethod
    def get_signing_key(self) -> Any:
        """Return the private signing key for token creation.

        The concrete type depends on the implementation (e.g., a PEM string,
        a cryptography key object, or a KMS key reference).
        """

    @abstractmethod
    def get_verification_key(self) -> Any:
        """Return the public verification key for token validation."""

    @abstractmethod
    def get_secret(self, name: str) -> str:
        """Retrieve a named secret (e.g., JWT secret, HMAC key)."""
