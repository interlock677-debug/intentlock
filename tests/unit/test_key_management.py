"""Comprehensive tests for the key-management subsystem.

Covers:
    - VersionedKeyManager (rotation, versioning, persistence, HSM delegation)
    - EnvKeyManager (missing branches)
    - KMSKeyManager (interface contract, fail-closed behavior)
    - SimulatedHSMKeyProvider (failure modes, key lifecycle)
    - Ed25519ExecutionTokenService (unknown key ID path)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.application.interfaces.hsm_key_provider import (
    HSMKeyNotFoundError,
    HSMKeyProvider,
    HSMUnavailableError,
    SimulatedHSMKeyProvider,
)
from app.application.interfaces.key_manager import KeyManager
from app.domain.exceptions.domain_errors import ExecutionTokenError
from app.infrastructure.security.ed25519_execution_token_service import (
    Ed25519ExecutionTokenService,
)
from app.infrastructure.security.env_key_manager import EnvKeyManager
from app.infrastructure.security.kms_key_manager import KMSKeyManager
from app.infrastructure.security.memory_nonce_store import MemoryNonceStore
from app.infrastructure.security.versioned_key_manager import VersionedKeyManager


# --------------------------------------------------------------------------- #
# Test double: a real HSM provider that signs with in-memory keys
# --------------------------------------------------------------------------- #


class _SigningHSMProvider(HSMKeyProvider):
    """Test double that actually signs, simulating a real HSM."""

    def __init__(self) -> None:
        self._keys: dict[str, Ed25519PrivateKey] = {}
        self._unavailable = False

    def import_private_key(self, key_id: str, key: Ed25519PrivateKey) -> None:
        self._keys[key_id] = key

    def set_unavailable(self, unavailable: bool = True) -> None:
        self._unavailable = unavailable

    def sign(self, key_id: str, data: bytes) -> bytes:
        if self._unavailable:
            raise HSMUnavailableError("Simulated HSM is unavailable")
        if key_id not in self._keys:
            raise HSMKeyNotFoundError(f"Key not found in HSM: {key_id}")
        return self._keys[key_id].sign(data)

    def get_public_key(self, key_id: str) -> Ed25519PublicKey:
        if self._unavailable:
            raise HSMUnavailableError("Simulated HSM is unavailable")
        if key_id not in self._keys:
            raise HSMKeyNotFoundError(f"Key not found in HSM: {key_id}")
        return self._keys[key_id].public_key()

    def key_exists(self, key_id: str) -> bool:
        if self._unavailable:
            return False
        return key_id in self._keys

    def health_check(self) -> bool:
        return not self._unavailable


# --------------------------------------------------------------------------- #
# VersionedKeyManager — basic key retrieval
# --------------------------------------------------------------------------- #


def test_versioned_key_manager_initializes_with_active_key() -> None:
    km = VersionedKeyManager()
    assert km.active_key_id
    assert km.get_key_ids() == [km.active_key_id]

    # Active key is retrievable for signing and verification.
    sk = km.get_signing_key()
    vk = km.get_verification_key()
    assert sk is not None
    assert vk is not None
    assert sk.public_key().public_bytes_raw() == vk.public_bytes_raw()


def test_versioned_key_manager_get_signing_key_with_explicit_active_id() -> None:
    km = VersionedKeyManager()
    sk = km.get_signing_key(km.active_key_id)
    assert sk is not None


def test_versioned_key_manager_get_signing_key_unknown_id_raises() -> None:
    km = VersionedKeyManager()
    with pytest.raises(ValueError):
        km.get_signing_key("key-nonexistent")


def test_versioned_key_manager_get_verification_key_unknown_id_raises() -> None:
    km = VersionedKeyManager()
    with pytest.raises(KeyError):
        km.get_verification_key("key-nonexistent")


def test_versioned_key_manager_get_secret_jwt() -> None:
    km = VersionedKeyManager(jwt_secret="super-secret-value")
    assert km.get_secret("jwt_secret") == "super-secret-value"


def test_versioned_key_manager_get_secret_missing_jwt_raises() -> None:
    km = VersionedKeyManager()
    with pytest.raises(KeyError):
        km.get_secret("jwt_secret")


def test_versioned_key_manager_get_secret_unknown_name_raises() -> None:
    km = VersionedKeyManager(jwt_secret="secret")
    with pytest.raises(KeyError):
        km.get_secret("unknown_secret")


# --------------------------------------------------------------------------- #
# VersionedKeyManager — signing
# --------------------------------------------------------------------------- #


def test_versioned_key_manager_sign_with_active_key() -> None:
    km = VersionedKeyManager()
    data = b"hello world"
    sig = km.sign(data)
    assert len(sig) == 64  # Ed25519 signature size
    km.get_verification_key().verify(sig, data)


def test_versioned_key_manager_sign_with_explicit_key_id() -> None:
    km = VersionedKeyManager()
    data = b"payload"
    sig = km.sign(data, km.active_key_id)
    km.get_verification_key(km.active_key_id).verify(sig, data)


def test_versioned_key_manager_sign_with_unknown_key_id_raises() -> None:
    km = VersionedKeyManager()
    with pytest.raises(KeyError):
        km.sign(b"data", "key-does-not-exist")


# --------------------------------------------------------------------------- #
# VersionedKeyManager — rotation
# --------------------------------------------------------------------------- #


def test_versioned_key_manager_rotation_changes_active_key() -> None:
    km = VersionedKeyManager()
    old_active = km.active_key_id
    new_active = km.rotate()

    assert new_active != old_active
    assert km.active_key_id == new_active
    assert km.get_key_ids() == [new_active, old_active]


def test_versioned_key_manager_old_key_still_verifies_after_rotation() -> None:
    km = VersionedKeyManager()
    old_active = km.active_key_id
    data = b"token-data"
    old_sig = km.sign(data, old_active)

    km.rotate()

    # Old key still verifies during the grace period.
    old_vk = km.get_verification_key(old_active)
    old_vk.verify(old_sig, data)


def test_versioned_key_manager_new_key_signs_after_rotation() -> None:
    km = VersionedKeyManager()
    km.rotate()
    new_active = km.active_key_id
    data = b"new-token"
    sig = km.sign(data, new_active)
    km.get_verification_key(new_active).verify(sig, data)


def test_versioned_key_manager_old_active_cannot_sign_after_rotation() -> None:
    km = VersionedKeyManager()
    old_active = km.active_key_id
    km.rotate()

    # The old key is no longer the active signing key.
    with pytest.raises(ValueError):
        km.get_signing_key(old_active)


def test_versioned_key_manager_retired_keys_deleted_after_rotation_limit() -> None:
    km = VersionedKeyManager()
    first_key = km.active_key_id
    km.rotate()  # second key
    second_key = km.active_key_id
    km.rotate()  # third key
    third_key = km.active_key_id
    km.rotate()  # fourth key

    # Only the last 3 keys (active + 2 previous) remain.
    key_ids = km.get_key_ids()
    assert len(key_ids) == 3
    assert first_key not in key_ids
    assert second_key in key_ids
    assert third_key in key_ids
    assert km.active_key_id in key_ids

    # The retired key is no longer retrievable.
    with pytest.raises(KeyError):
        km.get_verification_key(first_key)


def test_versioned_key_manager_rotation_persists_metadata(tmp_path: Path) -> None:
    key_dir = tmp_path / "keys"
    km = VersionedKeyManager(key_dir=str(key_dir))
    first_key = km.active_key_id
    km.rotate()
    second_key = km.active_key_id

    # Reload from disk — metadata and keys persist.
    km2 = VersionedKeyManager(key_dir=str(key_dir))
    assert km2.active_key_id == second_key
    assert km2.get_key_ids() == [second_key, first_key]

    # Keys are actually loadable from disk.
    vk = km2.get_verification_key(first_key)
    assert vk is not None


def test_versioned_key_manager_rotation_deletes_retired_key_file(tmp_path: Path) -> None:
    key_dir = tmp_path / "keys"
    km = VersionedKeyManager(key_dir=str(key_dir))
    first_key = km.active_key_id
    km.rotate()
    km.rotate()
    km.rotate()

    # The first key's PEM file should be deleted.
    assert not (key_dir / f"{first_key}.pem").exists()


# --------------------------------------------------------------------------- #
# VersionedKeyManager — persistence
# --------------------------------------------------------------------------- #


def test_versioned_key_manager_persists_keys_to_disk(tmp_path: Path) -> None:
    key_dir = tmp_path / "keys"
    km = VersionedKeyManager(key_dir=str(key_dir))
    key_id = km.active_key_id

    assert (key_dir / f"{key_id}.pem").exists()
    assert (key_dir / "metadata.json").exists()

    metadata = json.loads((key_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["active_key_id"] == key_id
    assert metadata["previous_key_ids"] == []


def test_versioned_key_manager_reloads_from_disk(tmp_path: Path) -> None:
    key_dir = tmp_path / "keys"
    km1 = VersionedKeyManager(key_dir=str(key_dir))
    key_id = km1.active_key_id
    data = b"persisted-data"
    sig = km1.sign(data)

    # New instance loads the same key from disk.
    km2 = VersionedKeyManager(key_dir=str(key_dir))
    assert km2.active_key_id == key_id
    km2.get_verification_key().verify(sig, data)


def test_versioned_key_manager_loads_previous_keys_from_metadata(tmp_path: Path) -> None:
    key_dir = tmp_path / "keys"
    km1 = VersionedKeyManager(key_dir=str(key_dir))
    first_key = km1.active_key_id
    km1.rotate()
    second_key = km1.active_key_id

    # Manually corrupt metadata to include an extra previous key.
    metadata_file = key_dir / "metadata.json"
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    metadata["previous_key_ids"] = [first_key, "key-ghost"]
    metadata_file.write_text(json.dumps(metadata), encoding="utf-8")

    km2 = VersionedKeyManager(key_dir=str(key_dir))
    assert km2.active_key_id == second_key
    assert km2.get_key_ids() == [second_key, first_key, "key-ghost"]

    # Ghost key is not loadable.
    with pytest.raises(KeyError):
        km2.get_verification_key("key-ghost")


def test_versioned_key_manager_rotate_with_empty_active_key(tmp_path: Path) -> None:
    """Cover the defensive branch where the active key ID is empty."""
    key_dir = tmp_path / "keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    (key_dir / "metadata.json").write_text(
        json.dumps({"active_key_id": "", "previous_key_ids": []}),
        encoding="utf-8",
    )

    km = VersionedKeyManager(key_dir=str(key_dir))
    assert km.active_key_id == ""

    # Rotating with an empty active key must still produce a valid key.
    new_id = km.rotate()
    assert new_id
    assert km.active_key_id == new_id
    assert km.get_key_ids() == [new_id]


def test_versioned_key_manager_delete_ghost_key_file(tmp_path: Path) -> None:
    """Cover the branch where a retired key has no file on disk."""
    key_dir = tmp_path / "keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    (key_dir / "metadata.json").write_text(
        json.dumps(
            {
                "active_key_id": "key-active",
                "previous_key_ids": ["key-ghost-1", "key-ghost-2", "key-ghost-3"],
            }
        ),
        encoding="utf-8",
    )

    km = VersionedKeyManager(key_dir=str(key_dir))
    assert km.active_key_id == "key-active"

    # Rotating pushes the active key into previous and retires ghosts.
    # Each rotation retires one key beyond the retention limit (2 previous).
    km.rotate()  # retires key-ghost-3
    km.rotate()  # retires key-ghost-2
    km.rotate()  # retires key-ghost-1
    key_ids = km.get_key_ids()
    assert len(key_ids) == 3
    assert "key-ghost-1" not in key_ids
    assert "key-ghost-2" not in key_ids
    assert "key-ghost-3" not in key_ids


# --------------------------------------------------------------------------- #
# VersionedKeyManager — HSM delegation
# --------------------------------------------------------------------------- #


def _make_hsm_versioned_key_manager(tmp_path: Path) -> tuple[VersionedKeyManager, _SigningHSMProvider]:
    """Create a VersionedKeyManager backed by an HSM provider.

    The key is persisted to disk first (via a key_dir), then loaded into
    the HSM provider, and finally a new manager instance is created with
    the HSM provider so that signing is delegated to the HSM.
    """
    key_dir = tmp_path / "keys"
    hsm = _SigningHSMProvider()

    # Phase 1: create a manager with a key_dir to persist keys.
    seed = VersionedKeyManager(key_dir=str(key_dir))
    key_id = seed.active_key_id
    signing_key = seed.get_signing_key()

    # Phase 2: export the private key to the HSM provider.
    hsm.import_private_key(key_id, signing_key)

    # Phase 3: create the HSM-backed manager using the same key_dir so
    # the metadata/keys match what the HSM holds.
    km = VersionedKeyManager(key_dir=str(key_dir), hsm_provider=hsm)
    assert km.active_key_id == key_id
    return km, hsm


def test_versioned_key_manager_hsm_delegates_signing(tmp_path: Path) -> None:
    km, _ = _make_hsm_versioned_key_manager(tmp_path)

    data = b"hsm-signed-data"
    sig = km.sign(data)
    assert len(sig) == 64
    km.get_verification_key().verify(sig, data)


def test_versioned_key_manager_hsm_sign_with_explicit_key_id(tmp_path: Path) -> None:
    km, _ = _make_hsm_versioned_key_manager(tmp_path)

    data = b"data"
    sig = km.sign(data, km.active_key_id)
    km.get_verification_key(km.active_key_id).verify(sig, data)


def test_versioned_key_manager_hsm_unavailable_fails_closed(tmp_path: Path) -> None:
    km, hsm = _make_hsm_versioned_key_manager(tmp_path)
    hsm.set_unavailable(True)

    with pytest.raises(PermissionError):
        km.sign(b"data")


def test_versioned_key_manager_hsm_get_signing_key_raises_permission_error(tmp_path: Path) -> None:
    km, _ = _make_hsm_versioned_key_manager(tmp_path)

    with pytest.raises(PermissionError):
        km.get_signing_key()


def test_versioned_key_manager_hsm_unknown_key_id_raises(tmp_path: Path) -> None:
    km, _ = _make_hsm_versioned_key_manager(tmp_path)

    with pytest.raises(HSMKeyNotFoundError):
        km.sign(b"data", "key-not-in-hsm")


# --------------------------------------------------------------------------- #
# EnvKeyManager — missing branches
# --------------------------------------------------------------------------- #


def test_env_key_manager_unknown_signing_key_id_raises() -> None:
    km = EnvKeyManager(jwt_secret="secret")
    with pytest.raises(KeyError):
        km.get_signing_key("key-unknown")


def test_env_key_manager_unknown_verification_key_id_raises() -> None:
    km = EnvKeyManager(jwt_secret="secret")
    with pytest.raises(KeyError):
        km.get_verification_key("key-unknown")


def test_env_key_manager_active_key_id_and_key_ids() -> None:
    km = EnvKeyManager(jwt_secret="secret")
    assert km.active_key_id == "ed25519-default"
    assert km.get_key_ids() == ["ed25519-default"]


def test_env_key_manager_sign_and_verify() -> None:
    km = EnvKeyManager(jwt_secret="secret")
    data = b"env-key-data"
    sig = km.sign(data)
    km.get_verification_key().verify(sig, data)


# --------------------------------------------------------------------------- #
# KMSKeyManager
# --------------------------------------------------------------------------- #


def test_kms_key_manager_contract() -> None:
    km = KMSKeyManager(provider="aws-kms", key_id="kms-key-123", jwt_secret_name="jwt-secret")
    assert km.active_key_id == "kms-key-123"
    assert km.get_key_ids() == ["kms-key-123"]

    ref = km.get_signing_key()
    assert ref == {"provider": "aws-kms", "key_id": "kms-key-123"}

    vref = km.get_verification_key()
    assert vref == {"provider": "aws-kms", "key_id": "kms-key-123"}


def test_kms_key_manager_unknown_signing_key_id_raises() -> None:
    km = KMSKeyManager(provider="aws-kms", key_id="kms-key-123", jwt_secret_name="jwt-secret")
    with pytest.raises(KeyError):
        km.get_signing_key("kms-key-other")


def test_kms_key_manager_unknown_verification_key_id_raises() -> None:
    km = KMSKeyManager(provider="aws-kms", key_id="kms-key-123", jwt_secret_name="jwt-secret")
    with pytest.raises(KeyError):
        km.get_verification_key("kms-key-other")


def test_kms_key_manager_get_secret_requires_external_store() -> None:
    km = KMSKeyManager(provider="aws-kms", key_id="kms-key-123", jwt_secret_name="jwt-secret")
    with pytest.raises(NotImplementedError):
        km.get_secret("jwt-secret")


def test_kms_key_manager_get_secret_unknown_name_raises() -> None:
    km = KMSKeyManager(provider="aws-kms", key_id="kms-key-123", jwt_secret_name="jwt-secret")
    with pytest.raises(KeyError):
        km.get_secret("unknown-secret")


def test_kms_key_manager_sign_requires_provider_sdk() -> None:
    km = KMSKeyManager(provider="aws-kms", key_id="kms-key-123", jwt_secret_name="jwt-secret")
    with pytest.raises(NotImplementedError):
        km.sign(b"data")


def test_kms_key_manager_sign_unknown_key_id_raises() -> None:
    km = KMSKeyManager(provider="aws-kms", key_id="kms-key-123", jwt_secret_name="jwt-secret")
    with pytest.raises(KeyError):
        km.sign(b"data", "kms-key-other")


# --------------------------------------------------------------------------- #
# SimulatedHSMKeyProvider
# --------------------------------------------------------------------------- #


def test_simulated_hsm_import_and_retrieve() -> None:
    hsm = SimulatedHSMKeyProvider()
    key = Ed25519PrivateKey.generate()
    hsm.import_key("key-1", key.public_key())

    assert hsm.get_imported_key_ids() == ["key-1"]
    assert hsm.key_exists("key-1") is True
    assert hsm.key_exists("key-2") is False
    assert hsm.health_check() is True

    pub = hsm.get_public_key("key-1")
    assert pub.public_bytes_raw() == key.public_key().public_bytes_raw()


def test_simulated_hsm_unavailable_fails_closed() -> None:
    hsm = SimulatedHSMKeyProvider()
    key = Ed25519PrivateKey.generate()
    hsm.import_key("key-1", key.public_key())
    hsm.set_unavailable(True)

    assert hsm.health_check() is False
    assert hsm.key_exists("key-1") is False

    with pytest.raises(HSMUnavailableError):
        hsm.sign("key-1", b"data")

    with pytest.raises(HSMUnavailableError):
        hsm.get_public_key("key-1")


def test_simulated_hsm_sign_unknown_key_raises() -> None:
    hsm = SimulatedHSMKeyProvider()
    with pytest.raises(HSMKeyNotFoundError):
        hsm.sign("key-missing", b"data")


def test_simulated_hsm_get_public_key_unknown_key_raises() -> None:
    hsm = SimulatedHSMKeyProvider()
    with pytest.raises(HSMKeyNotFoundError):
        hsm.get_public_key("key-missing")


def test_simulated_hsm_sign_valid_key_raises_not_implemented() -> None:
    hsm = SimulatedHSMKeyProvider()
    key = Ed25519PrivateKey.generate()
    hsm.import_key("key-1", key.public_key())

    # The simulated HSM delegates signing to the VersionedKeyManager.
    with pytest.raises(NotImplementedError):
        hsm.sign("key-1", b"data")


def test_simulated_hsm_import_resets_unavailable() -> None:
    hsm = SimulatedHSMKeyProvider()
    hsm.set_unavailable(True)
    assert hsm.health_check() is False

    key = Ed25519PrivateKey.generate()
    hsm.import_key("key-1", key.public_key())
    assert hsm.health_check() is True


# --------------------------------------------------------------------------- #
# Ed25519ExecutionTokenService — unknown key ID path
# --------------------------------------------------------------------------- #


def test_execution_token_unknown_kid_rejected() -> None:
    km = EnvKeyManager(jwt_secret="secret")
    nonce_store = MemoryNonceStore()
    svc = Ed25519ExecutionTokenService(key_manager=km, nonce_store=nonce_store)

    # Create a token with a kid that doesn't exist in the key manager.
    sk = km.get_signing_key()
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "agent",
            "type": "execution",
            "tool": "tool",
            "iat": now,
            "nbf": now,
            "exp": now + 10,
            "jti": str(uuid4()),
        },
        sk,
        algorithm="EdDSA",
        headers={"kid": "key-does-not-exist"},
    )

    with pytest.raises(ExecutionTokenError) as exc_info:
        svc.verify_execution_token(token)
    assert "Unknown key ID" in str(exc_info.value)


def test_execution_token_rotation_old_key_still_verifies() -> None:
    km = VersionedKeyManager()
    nonce_store = MemoryNonceStore()
    svc = Ed25519ExecutionTokenService(key_manager=km, nonce_store=nonce_store)

    # Sign with the original active key.
    token = svc.create_execution_token(
        agent_id="agent-1",
        tool="tool-1",
        ttl_seconds=30,
    )

    # Rotate the key.
    km.rotate()

    # The old token still verifies because the old key is in the grace period.
    payload = svc.verify_execution_token(token)
    assert payload["sub"] == "agent-1"
    assert payload["tool"] == "tool-1"


def test_execution_token_rotation_new_key_signs() -> None:
    km = VersionedKeyManager()
    nonce_store = MemoryNonceStore()
    svc = Ed25519ExecutionTokenService(key_manager=km, nonce_store=nonce_store)

    km.rotate()
    token = svc.create_execution_token(
        agent_id="agent-2",
        tool="tool-2",
        ttl_seconds=30,
    )
    payload = svc.verify_execution_token(token)
    assert payload["sub"] == "agent-2"


def test_execution_token_jwks_includes_all_keys_after_rotation() -> None:
    km = VersionedKeyManager()
    nonce_store = MemoryNonceStore()
    svc = Ed25519ExecutionTokenService(key_manager=km, nonce_store=nonce_store)

    first_key = km.active_key_id
    km.rotate()
    second_key = km.active_key_id

    jwks = svc.get_jwks()
    kids = {key["kid"] for key in jwks["keys"]}
    assert first_key in kids
    assert second_key in kids