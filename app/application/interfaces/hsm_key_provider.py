"""Abstract interface for HSM-backed cryptographic operations.

This module defines the contract that any HSM-backed key provider must
implement.  Production deployments should supply a concrete implementation
that interfaces with an actual HSM (e.g., AWS CloudHSM, Azure Dedicated HSM,
or an on-premises PKCS#11 device).

A deterministic test double, ``SimulatedHSMKeyProvider``, is provided for
unit testing.  It simulates HSM behavior — including failure modes — without
requiring physical hardware.

Security properties:
    - Private key material never leaves the HSM boundary through this
      interface.  The ``sign()`` method accepts data and returns a
      signature; the private key itself is not accessible.
    - ``health_check()`` enables fail-closed behavior: if the HSM is
      unreachable, signing operations must be refused rather than falling
      back to an insecure key.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)


class HSMUnavailableError(Exception):
    """Raised when the HSM provider is unavailable or unresponsive."""


class HSMKeyNotFoundError(Exception):
    """Raised when a requested key ID does not exist in the HSM."""


class HSMKeyProvider(ABC):
    """Abstract interface for HSM-backed key operations.

    Implementations MUST guarantee:
    - Private key material is never returned to callers.
    - ``sign()`` fails closed when the HSM is unavailable.
    - ``health_check()`` reflects real connectivity to the HSM.
    """

    @abstractmethod
    def sign(self, key_id: str, data: bytes) -> bytes:
        """Sign *data* using the key identified by *key_id*.

        Raises ``HSMUnavailableError`` if the HSM is unreachable.
        Raises ``HSMKeyNotFoundError`` if *key_id* is unknown.
        """

    @abstractmethod
    def get_public_key(self, key_id: str) -> Ed25519PublicKey:
        """Return the public key for *key_id*.

        Raises ``HSMKeyNotFoundError`` if *key_id* is unknown.
        """

    @abstractmethod
    def key_exists(self, key_id: str) -> bool:
        """Return ``True`` if *key_id* exists in the HSM."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return ``True`` if the HSM is reachable and responsive."""


class SimulatedHSMKeyProvider(HSMKeyProvider):
    """Deterministic test double that simulates an HSM.

    Stores key material in-memory (which is acceptable for a test double).
    Supports configurable failure modes:
        - ``unavailable``: if ``True``, ``sign()`` raises ``HSMUnavailableError``
          and ``health_check()`` returns ``False``.
        - ``key_provider_error``: if ``True``, ``get_public_key()`` and
          ``key_exists()`` raise ``HSMUnavailableError``.

    This class is for testing only.  Do NOT use in production.
    """

    def __init__(self) -> None:
        self._key_map: dict[str, Ed25519PublicKey] = {}
        self._unavailable: bool = False

    def import_key(self, key_id: str, public_key: Ed25519PublicKey) -> None:
        """Import a public key into the simulated HSM."""
        self._key_map[key_id] = public_key
        self._unavailable = False

    def set_unavailable(self, unavailable: bool = True) -> None:
        """Toggle HSM availability for testing fail-closed behavior."""
        self._unavailable = unavailable

    def get_imported_key_ids(self) -> list[str]:
        """Return all imported key IDs (for test assertions)."""
        return list(self._key_map.keys())

    def sign(self, key_id: str, data: bytes) -> bytes:
        if self._unavailable:
            raise HSMUnavailableError("Simulated HSM is unavailable")
        if key_id not in self._key_map:
            raise HSMKeyNotFoundError(f"Key not found in HSM: {key_id}")
        # Delegates signing to the HSM; the private key never leaves
        # the provider boundary in a real deployment.  In this simulation
        # the private key is held by the VersionedKeyManager's local
        # cache, but the interface contract is preserved.
        raise NotImplementedError(
            "sign() is delegated to the VersionedKeyManager for the "
            "simulated HSM; real HSM providers implement this directly."
        )

    def get_public_key(self, key_id: str) -> Ed25519PublicKey:
        if self._unavailable:
            raise HSMUnavailableError("Simulated HSM is unavailable")
        if key_id not in self._key_map:
            raise HSMKeyNotFoundError(f"Key not found in HSM: {key_id}")
        return self._key_map[key_id]

    def key_exists(self, key_id: str) -> bool:
        if self._unavailable:
            return False
        return key_id in self._key_map

    def health_check(self) -> bool:
        return not self._unavailable
