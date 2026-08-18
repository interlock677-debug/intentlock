"""Tests for path traversal protection in key managers."""

import pytest

from app.infrastructure.security.env_key_manager import EnvKeyManager
from app.infrastructure.security.versioned_key_manager import VersionedKeyManager


def test_versioned_key_manager_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="Invalid key directory path"):
        VersionedKeyManager(key_dir="../../../etc/passwd")


def test_versioned_key_manager_accepts_relative_path() -> None:
    manager = VersionedKeyManager(key_dir="keys")
    assert manager.active_key_id is not None


def test_versioned_key_manager_accepts_absolute_path() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = VersionedKeyManager(key_dir=tmpdir)
        assert manager.active_key_id is not None


def test_env_key_manager_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="Invalid execution key path"):
        EnvKeyManager(
            jwt_secret="test-secret-key-that-is-at-least-32-characters-long",
            execution_key_path="../../../etc/passwd",
        )


def test_env_key_manager_accepts_relative_path() -> None:
    manager = EnvKeyManager(
        jwt_secret="test-secret-key-that-is-at-least-32-characters-long",
        execution_key_path="keys/execution_key.pem",
    )
    assert manager.active_key_id is not None


def test_env_key_manager_rejects_path_traversal_with_dotdot() -> None:
    with pytest.raises(ValueError, match="Invalid execution key path"):
        EnvKeyManager(
            jwt_secret="test-secret-key-that-is-at-least-32-characters-long",
            execution_key_path="keys/../../etc/passwd",
        )

