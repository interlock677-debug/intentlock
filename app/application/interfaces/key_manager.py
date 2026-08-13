from abc import ABC, abstractmethod
from typing import Any


class KeyManager(ABC):
    """Port for cryptographic key storage and retrieval.

    Production implementations should delegate to external key-management
    systems (AWS KMS, Google Cloud KMS, HashiCorp Vault, HSM). The
    application must never log or expose private key material.

    Key versioning:
        - ``active_key_id`` identifies the key used for signing new tokens.
        - ``get_key_ids()`` returns all keys still valid for verification
          (active + previous).  This enables seamless key rotation: tokens
          signed with a previous key remain verifiable until they expire.
        - ``key_id`` parameters on signing/verification methods allow callers
          to explicitly select a key.  When ``None`` the active key is used.
    """

    @abstractmethod
    def get_signing_key(self, key_id: str | None = None) -> Any:
        """Return the private signing key for token creation.

        The concrete type depends on the implementation (e.g., a PEM string,
        a cryptography key object, or a KMS key reference).  ``key_id``
        selects a specific key; ``None`` uses the active key.

        HSM-backed implementations should prefer overriding ``sign()``
        rather than exposing private key material through this method.
        """

    @abstractmethod
    def get_verification_key(self, key_id: str | None = None) -> Any:
        """Return the public verification key for token validation.

        ``key_id`` selects a specific key; ``None`` uses the active key.
        """

    @abstractmethod
    def get_secret(self, name: str) -> str:
        """Retrieve a named secret (e.g., JWT secret, HMAC key)."""

    @property
    @abstractmethod
    def active_key_id(self) -> str:
        """Return the ID of the current active signing key."""

    @abstractmethod
    def get_key_ids(self) -> list[str]:
        """Return all valid key IDs (active + previous).

        Used to populate JWKS so that clients can verify tokens signed
        with any still-valid key during a rotation grace period.
        """

    def sign(self, data: bytes, key_id: str | None = None) -> bytes:
        """Sign arbitrary data using the specified key.

        The default implementation delegates to ``get_signing_key()``,
        which returns the raw private key.  HSM-backed implementations
        must override this method to perform signing through the HSM
        without ever exposing private key material to application code.
        """
        key = self.get_signing_key(key_id)
        signature = key.sign(data)
        return bytes(signature)
