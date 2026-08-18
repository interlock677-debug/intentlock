"""Versioned key manager with rotation support and optional HSM delegation.

This provider is suitable for production deployments that store Ed25519
keys on a trusted local filesystem.  For true HSM/KMS integration, supply
an ``HSMKeyProvider`` — see ``SimulatedHSMKeyProvider`` for a test double.

Security boundaries:
    - Private key material is loaded into memory only within this class.
    - When an HSM provider is configured, signing is delegated to the HSM
      via the ``HSMKeyProvider.sign()`` interface; private keys never leave
      the HSM boundary.
    - The ``get_signing_key()`` method raises ``PermissionError`` when an
      HSM provider is active, because private key material should not be
      exposed to application code in that configuration.
"""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.application.interfaces.hsm_key_provider import HSMKeyProvider
from app.application.interfaces.key_manager import KeyManager

logger = logging.getLogger("intentlock.keymanager")

_MAX_PREVIOUS_KEYS = 2


class VersionedKeyManager(KeyManager):
    """Production key manager with versioned Ed25519 keys and rotation.

    Manages multiple Ed25519 key pairs with UUID-based version IDs.
    The *active* key is used for signing new tokens; *all* valid keys
    (active + previous) are available for verification during a rotation
    grace period.  Keys are persisted as PEM files in *key_dir*.
    """

    def __init__(
        self,
        *,
        key_dir: str | None = None,
        jwt_secret: str | None = None,
        hsm_provider: HSMKeyProvider | None = None,
    ) -> None:
        if key_dir is not None:
            if ".." in Path(key_dir).parts:
                msg = f"Invalid key directory path: {key_dir}"
                raise ValueError(msg)
            self._key_dir: Path | None = Path(key_dir).resolve()
        else:
            self._key_dir = None
        self._jwt_secret = jwt_secret
        self._hsm_provider = hsm_provider
        self._keys: dict[str, Ed25519PrivateKey] = {}
        self._active_key_id: str = ""
        self._previous_key_ids: list[str] = []
        self._load_or_initialize()

    # ------------------------------------------------------------------ #
    # KeyManager interface
    # ------------------------------------------------------------------ #

    @property
    def active_key_id(self) -> str:
        return self._active_key_id

    def get_key_ids(self) -> list[str]:
        """Return active + all previous key IDs (for JWKS)."""
        return [self._active_key_id] + list(self._previous_key_ids)

    def get_signing_key(self, key_id: str | None = None) -> Ed25519PrivateKey:
        if self._hsm_provider is not None:
            msg = (
                "get_signing_key() is not available when an HSM provider "
                "is configured. Use sign() instead."
            )
            raise PermissionError(msg)
        if key_id is None:
            key_id = self._active_key_id
        elif key_id != self._active_key_id:
            msg = f"Key {key_id} is not the active signing key"
            raise ValueError(msg)
        return self._get_key(key_id)

    def get_verification_key(self, key_id: str | None = None) -> Ed25519PublicKey:
        if key_id is None:
            key_id = self._active_key_id
        return self._get_key(key_id).public_key()

    def get_secret(self, name: str) -> str:
        if name == "jwt_secret":
            if self._jwt_secret is None:
                msg = "JWT secret not configured"
                raise KeyError(msg)
            return self._jwt_secret
        msg = f"Unknown secret requested: {name}"
        raise KeyError(msg)

    # ------------------------------------------------------------------ #
    # Signing — delegates to HSM when configured, else uses local key
    # ------------------------------------------------------------------ #

    def sign(self, data: bytes, key_id: str | None = None) -> bytes:
        if self._hsm_provider is not None:
            if not self._hsm_provider.health_check():
                msg = "HSM provider is unavailable"
                raise PermissionError(msg)
            if key_id is None:
                key_id = self._active_key_id
            # HSM-backed signing: the private key never leaves the HSM.
            return self._hsm_provider.sign(key_id, data)
        # Local signing via the in-memory private key.
        key = self._get_key(key_id or self._active_key_id)
        return key.sign(data)

    # ------------------------------------------------------------------ #
    # Key rotation
    # ------------------------------------------------------------------ #

    def rotate(self) -> str:
        """Create a new active signing key, demoting the current one.

        The old active key becomes a *previous* key, remaining valid for
        verification during its token TTL.  Previous keys beyond the
        retention limit (``_MAX_PREVIOUS_KEYS``) are deleted.

        Returns the new active key ID.
        """
        old_active = self._active_key_id
        new_id = self._generate_key_id()
        new_key = Ed25519PrivateKey.generate()
        self._keys[new_id] = new_key
        self._save_key(new_id, new_key)
        self._active_key_id = new_id

        if old_active:
            self._previous_key_ids.insert(0, old_active)
            while len(self._previous_key_ids) > _MAX_PREVIOUS_KEYS:
                retired = self._previous_key_ids.pop()
                self._delete_key(retired)

        self._save_metadata()
        logger.info(
            "Key rotated: new active=%s, previous=%s", new_id, old_active
        )
        return new_id

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _generate_key_id(self) -> str:
        return f"key-{secrets.token_hex(8)}"

    def _get_key(self, key_id: str) -> Ed25519PrivateKey:
        if key_id not in self._keys:
            key = self._load_key(key_id)
            if key is None:
                msg = f"Key not found: {key_id}"
                raise KeyError(msg)
            self._keys[key_id] = key
        return self._keys[key_id]

    def _load_or_initialize(self) -> None:
        if self._key_dir is None:
            self._initialize_new_key()
            return
        self._key_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = self._key_dir / "metadata.json"
        if metadata_file.exists():
            self._load_metadata(metadata_file)
        else:
            self._initialize_new_key()

    def _initialize_new_key(self) -> None:
        key_id = self._generate_key_id()
        key = Ed25519PrivateKey.generate()
        self._keys[key_id] = key
        self._active_key_id = key_id
        self._save_key(key_id, key)
        self._save_metadata()

    def _load_metadata(self, metadata_file: Path) -> None:
        data = json.loads(metadata_file.read_text(encoding="utf-8"))
        self._active_key_id = data["active_key_id"]
        self._previous_key_ids = list(data.get("previous_key_ids", []))

    def _save_metadata(self) -> None:
        if self._key_dir is None:
            return
        metadata = {
            "active_key_id": self._active_key_id,
            "previous_key_ids": self._previous_key_ids,
        }
        (self._key_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

    def _save_key(self, key_id: str, key: Ed25519PrivateKey) -> None:
        if self._key_dir is None:
            return
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        (self._key_dir / f"{key_id}.pem").write_bytes(pem)

    def _load_key(self, key_id: str) -> Ed25519PrivateKey | None:
        if self._key_dir is None:
            return None
        key_file = self._key_dir / f"{key_id}.pem"
        if not key_file.exists():
            return None
        data = key_file.read_bytes()
        result = serialization.load_pem_private_key(data, password=None)
        return result  # type: ignore[return-value]

    def _delete_key(self, key_id: str) -> None:
        # Always remove the key from the in-memory cache so that retired
        # keys are never usable for verification, even when no key_dir is
        # configured (in-memory-only operation).
        self._keys.pop(key_id, None)
        if self._key_dir is None:
            return
        key_file = self._key_dir / f"{key_id}.pem"
        if key_file.exists():
            key_file.unlink()
