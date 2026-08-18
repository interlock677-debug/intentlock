import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IAMConfig:
    enabled: bool = False
    provider: str = "mock"
    entity_id: str = ""
    sso_url: str = ""
    x509_cert: str = ""
    client_id: str = ""
    client_secret: str = ""
    scim_base_url: str = ""
    scim_token: str = ""


class IAMAdapter(ABC):
    """Port for IAM integration."""

    @abstractmethod
    def provision_user(self, attributes: dict[str, Any]) -> dict[str, Any]:
        """Provision a user in the IAM system."""

    @abstractmethod
    def deprovision_user(self, user_id: str) -> None:
        """Deprovision a user from the IAM system."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the IAM is reachable."""


class MockIAMAdapter(IAMAdapter):
    """Mock IAM adapter for testing and development."""

    def __init__(self, config: IAMConfig | None = None) -> None:
        self._config = config or IAMConfig()
        self._users: dict[str, dict[str, Any]] = {}

    def provision_user(self, attributes: dict[str, Any]) -> dict[str, Any]:
        user_id = str(attributes.get("id", ""))
        self._users[user_id] = {
            "id": user_id,
            "email": attributes.get("email", ""),
            "role": attributes.get("role", "viewer"),
            "status": "active",
            "provisioned_at": datetime.now(tz=UTC).isoformat(),
        }
        logger.debug("Mock IAM user provisioned: %s", user_id)
        return self._users[user_id]

    def deprovision_user(self, user_id: str) -> None:
        if user_id in self._users:
            self._users[user_id]["status"] = "deprovisioned"
            logger.debug("Mock IAM user deprovisioned: %s", user_id)

    def health_check(self) -> bool:
        return True

    def get_users(self) -> dict[str, dict[str, Any]]:
        return dict(self._users)


class SAMLIAMAdapter(IAMAdapter):
    """SAML IAM adapter."""

    def __init__(self, config: IAMConfig | None = None) -> None:
        self._config = config or _load_iam_config()
        self._users: dict[str, dict[str, Any]] = {}

    def provision_user(self, attributes: dict[str, Any]) -> dict[str, Any]:
        if not self._config.enabled:
            return {}
        user_id = str(attributes.get("id", ""))
        self._users[user_id] = {
            "id": user_id,
            "email": attributes.get("email", ""),
            "role": attributes.get("role", "viewer"),
            "status": "active",
            "provider": "saml",
            "provisioned_at": datetime.now(tz=UTC).isoformat(),
        }
        logger.debug("SAML IAM user provisioned: %s", user_id)
        return self._users[user_id]

    def deprovision_user(self, user_id: str) -> None:
        if user_id in self._users:
            self._users[user_id]["status"] = "deprovisioned"
            logger.debug("SAML IAM user deprovisioned: %s", user_id)

    def health_check(self) -> bool:
        return self._config.enabled

    def get_users(self) -> dict[str, dict[str, Any]]:
        return dict(self._users)


class OIDCIAMAdapter(IAMAdapter):
    """OIDC IAM adapter."""

    def __init__(self, config: IAMConfig | None = None) -> None:
        self._config = config or _load_iam_config()
        self._users: dict[str, dict[str, Any]] = {}

    def provision_user(self, attributes: dict[str, Any]) -> dict[str, Any]:
        if not self._config.enabled:
            return {}
        user_id = str(attributes.get("id", ""))
        self._users[user_id] = {
            "id": user_id,
            "email": attributes.get("email", ""),
            "role": attributes.get("role", "viewer"),
            "status": "active",
            "provider": "oidc",
            "provisioned_at": datetime.now(tz=UTC).isoformat(),
        }
        logger.debug("OIDC IAM user provisioned: %s", user_id)
        return self._users[user_id]

    def deprovision_user(self, user_id: str) -> None:
        if user_id in self._users:
            self._users[user_id]["status"] = "deprovisioned"
            logger.debug("OIDC IAM user deprovisioned: %s", user_id)

    def health_check(self) -> bool:
        return self._config.enabled

    def get_users(self) -> dict[str, dict[str, Any]]:
        return dict(self._users)


class SCIMAdapter(IAMAdapter):
    """SCIM 2.0 adapter for user lifecycle management."""

    def __init__(self, config: IAMConfig | None = None) -> None:
        self._config = config or _load_iam_config()
        self._users: dict[str, dict[str, Any]] = {}

    def provision_user(self, attributes: dict[str, Any]) -> dict[str, Any]:
        if not self._config.enabled:
            return {}
        user_id = str(attributes.get("id", ""))
        scim_user = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": user_id,
            "userName": attributes.get("email", ""),
            "displayName": attributes.get("email", ""),
            "active": True,
            "meta": {
                "resourceType": "User",
                "created": datetime.now(tz=UTC).isoformat(),
            },
        }
        self._users[user_id] = scim_user
        logger.debug("SCIM user provisioned: %s", user_id)
        return scim_user

    def deprovision_user(self, user_id: str) -> None:
        if user_id in self._users:
            self._users[user_id]["active"] = False
            self._users[user_id]["meta"]["lastModified"] = datetime.now(tz=UTC).isoformat()
            logger.debug("SCIM user deprovisioned: %s", user_id)

    def health_check(self) -> bool:
        return self._config.enabled

    def get_users(self) -> dict[str, dict[str, Any]]:
        return dict(self._users)


def get_iam_adapter() -> IAMAdapter:
    settings = get_settings()
    provider = getattr(settings, "iam_provider", "mock")
    if provider == "saml":
        return SAMLIAMAdapter()
    if provider == "oidc":
        return OIDCIAMAdapter()
    if provider == "scim":
        return SCIMAdapter()
    return MockIAMAdapter()


def _load_iam_config() -> IAMConfig:
    settings = get_settings()
    return IAMConfig(
        enabled=getattr(settings, "iam_enabled", False),
        provider=getattr(settings, "iam_provider", "mock"),
        entity_id=getattr(settings, "saml_entity_id", ""),
        sso_url=getattr(settings, "saml_sso_url", ""),
        x509_cert=getattr(settings, "saml_x509_cert", ""),
        client_id=getattr(settings, "oidc_client_id", ""),
        client_secret=getattr(settings, "oidc_client_secret", ""),
        scim_base_url=getattr(settings, "scim_base_url", ""),
        scim_token=getattr(settings, "scim_token", ""),
    )
