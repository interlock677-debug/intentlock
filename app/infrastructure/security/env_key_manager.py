from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.application.interfaces.key_manager import KeyManager

_KEY_ID = "ed25519-default"


class EnvKeyManager(KeyManager):
    """Development/test key manager backed by environment variables.

    This implementation is suitable for development and test environments
    only. Production deployments MUST use a KMS-backed implementation.
    """

    def __init__(
        self,
        *,
        jwt_secret: str,
        execution_key_path: str | None = None,
    ) -> None:
        self._jwt_secret = jwt_secret
        self._execution_key_path = execution_key_path
        self._private_key: Ed25519PrivateKey | None = None

    @property
    def active_key_id(self) -> str:
        return _KEY_ID

    def get_key_ids(self) -> list[str]:
        return [_KEY_ID]

    def get_signing_key(self, key_id: str | None = None) -> Ed25519PrivateKey:
        if key_id is not None and key_id != _KEY_ID:
            msg = f"Unknown key ID: {key_id}"
            raise KeyError(msg)
        if self._private_key is None:
            self._private_key = self._load_or_create_private_key()
        return self._private_key

    def get_verification_key(self, key_id: str | None = None) -> object:
        if key_id is not None and key_id != _KEY_ID:
            msg = f"Unknown key ID: {key_id}"
            raise KeyError(msg)
        return self.get_signing_key().public_key()

    def get_secret(self, name: str) -> str:
        if name == "jwt_secret":
            return self._jwt_secret
        msg = f"Unknown secret requested: {name}"
        raise KeyError(msg)

    def _load_or_create_private_key(self) -> Ed25519PrivateKey:
        if self._execution_key_path and Path(self._execution_key_path).exists():
            data = Path(self._execution_key_path).read_bytes()
            return serialization.load_pem_private_key(data, password=None)  # type: ignore[return-value]

        key = Ed25519PrivateKey.generate()
        if self._execution_key_path:
            path = Path(self._execution_key_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        return key
