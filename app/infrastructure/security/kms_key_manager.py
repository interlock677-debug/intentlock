from typing import Any

from app.application.interfaces.key_manager import KeyManager


class KMSKeyManager(KeyManager):
    """Production key manager abstraction for external KMS systems.

    This class defines the interface contract for integrating with
    external key-management systems such as AWS KMS, Google Cloud KMS,
    or HashiCorp Vault. The actual integration requires provider-specific
    SDKs and credentials that must be configured by the deployment team.

    The application never holds private key material in process memory
    when using this implementation — signing operations are delegated
    to the external KMS.
    """

    def __init__(
        self,
        *,
        provider: str,
        key_id: str,
        jwt_secret_name: str,
    ) -> None:
        self._provider = provider
        self._key_id = key_id
        self._jwt_secret_name = jwt_secret_name

    @property
    def active_key_id(self) -> str:
        return self._key_id

    def get_key_ids(self) -> list[str]:
        return [self._key_id]

    def get_signing_key(self, key_id: str | None = None) -> Any:
        """Return a reference to the KMS signing key.

        The concrete return type depends on the provider SDK. For AWS KMS
        this would be a key ID/ARN; for Vault this would be a transit key
        path. The application must use the provider SDK to perform signing
        operations rather than retrieving raw key material.
        """
        if key_id is not None and key_id != self._key_id:
            msg = f"Unknown key ID: {key_id}"
            raise KeyError(msg)
        return {
            "provider": self._provider,
            "key_id": self._key_id,
        }

    def get_verification_key(self, key_id: str | None = None) -> Any:
        """Return a reference to the KMS public verification key."""
        if key_id is not None and key_id != self._key_id:
            msg = f"Unknown key ID: {key_id}"
            raise KeyError(msg)
        return {
            "provider": self._provider,
            "key_id": self._key_id,
        }

    def get_secret(self, name: str) -> str:
        """Retrieve a secret from the external secret store.

        The concrete implementation must use the provider's secret
        management API (e.g., AWS Secrets Manager, Vault KV store).
        """
        if name == self._jwt_secret_name:
            msg = (
                f"Secret '{name}' must be retrieved from the external "
                f"secret store ({self._provider}). Configure the provider "
                "SDK and implement the retrieval call."
            )
            raise NotImplementedError(msg)
        msg = f"Unknown secret requested: {name}"
        raise KeyError(msg)

    def sign(self, data: bytes, key_id: str | None = None) -> bytes:
        """Sign data through the external KMS.

        This method must be overridden by concrete KMS provider integrations
        that use the provider SDK (e.g., boto3 for AWS KMS). The default
        implementation raises NotImplementedError to ensure fail-closed
        behavior — signing through a KMS placeholder is never silent.
        """
        if key_id is not None and key_id != self._key_id:
            msg = f"Unknown key ID: {key_id}"
            raise KeyError(msg)
        msg = (
            f"KMS signing through provider '{self._provider}' "
            f"(key {self._key_id}) requires provider SDK integration. "
            "Implement sign() using the provider's signing API."
        )
        raise NotImplementedError(msg)
