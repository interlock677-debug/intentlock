from unittest.mock import MagicMock

import pytest

from app.infrastructure.integrations.iam_adapter import (
    IAMConfig,
    MockIAMAdapter,
    OIDCIAMAdapter,
    SAMLIAMAdapter,
    SCIMAdapter,
    _load_iam_config,
    get_iam_adapter,
)


def test_mock_iam_adapter_provision_user() -> None:
    adapter = MockIAMAdapter()
    user = adapter.provision_user({"id": "user-1", "email": "a@b.com", "role": "admin"})
    assert user["id"] == "user-1"
    assert user["email"] == "a@b.com"
    assert user["role"] == "admin"
    assert user["status"] == "active"


def test_mock_iam_adapter_deprovision_user() -> None:
    adapter = MockIAMAdapter()
    adapter.provision_user({"id": "user-1", "email": "a@b.com"})
    adapter.deprovision_user("user-1")
    assert adapter.get_users()["user-1"]["status"] == "deprovisioned"


def test_mock_iam_adapter_deprovision_missing_user() -> None:
    adapter = MockIAMAdapter()
    adapter.deprovision_user("nonexistent")


def test_mock_iam_adapter_health_check() -> None:
    adapter = MockIAMAdapter()
    assert adapter.health_check() is True


def test_mock_iam_adapter_get_users() -> None:
    adapter = MockIAMAdapter()
    adapter.provision_user({"id": "user-1"})
    users = adapter.get_users()
    assert "user-1" in users
    assert users["user-1"]["status"] == "active"


def test_saml_iam_adapter_disabled_provision() -> None:
    config = IAMConfig(enabled=False)
    adapter = SAMLIAMAdapter(config=config)
    user = adapter.provision_user({"id": "user-1"})
    assert user == {}


def test_saml_iam_adapter_enabled_provision() -> None:
    config = IAMConfig(enabled=True)
    adapter = SAMLIAMAdapter(config=config)
    user = adapter.provision_user({"id": "user-1", "email": "a@b.com"})
    assert user["id"] == "user-1"
    assert user["provider"] == "saml"


def test_saml_iam_adapter_deprovision_user() -> None:
    config = IAMConfig(enabled=True)
    adapter = SAMLIAMAdapter(config=config)
    adapter.provision_user({"id": "user-1", "email": "a@b.com"})
    adapter.deprovision_user("user-1")
    user = adapter.get_users()["user-1"]
    assert user["status"] == "deprovisioned"


def test_saml_iam_adapter_deprovision_missing_user() -> None:
    config = IAMConfig(enabled=True)
    adapter = SAMLIAMAdapter(config=config)
    adapter.deprovision_user("nonexistent")


def test_saml_iam_adapter_get_users() -> None:
    config = IAMConfig(enabled=True)
    adapter = SAMLIAMAdapter(config=config)
    adapter.provision_user({"id": "user-1"})
    assert "user-1" in adapter.get_users()


def test_saml_iam_adapter_health_check_disabled() -> None:
    config = IAMConfig(enabled=False)
    adapter = SAMLIAMAdapter(config=config)
    assert adapter.health_check() is False


def test_oidc_iam_adapter_disabled_provision() -> None:
    config = IAMConfig(enabled=False)
    adapter = OIDCIAMAdapter(config=config)
    user = adapter.provision_user({"id": "user-1"})
    assert user == {}


def test_oidc_iam_adapter_enabled_provision() -> None:
    config = IAMConfig(enabled=True)
    adapter = OIDCIAMAdapter(config=config)
    user = adapter.provision_user({"id": "user-1", "email": "a@b.com"})
    assert user["id"] == "user-1"
    assert user["provider"] == "oidc"


def test_oidc_iam_adapter_deprovision_user() -> None:
    config = IAMConfig(enabled=True)
    adapter = OIDCIAMAdapter(config=config)
    adapter.provision_user({"id": "user-1", "email": "a@b.com"})
    adapter.deprovision_user("user-1")
    user = adapter.get_users()["user-1"]
    assert user["status"] == "deprovisioned"


def test_oidc_iam_adapter_deprovision_missing_user() -> None:
    config = IAMConfig(enabled=True)
    adapter = OIDCIAMAdapter(config=config)
    adapter.deprovision_user("nonexistent")


def test_oidc_iam_adapter_get_users() -> None:
    config = IAMConfig(enabled=True)
    adapter = OIDCIAMAdapter(config=config)
    adapter.provision_user({"id": "user-1"})
    assert "user-1" in adapter.get_users()


def test_oidc_iam_adapter_health_check_enabled() -> None:
    config = IAMConfig(enabled=True)
    adapter = OIDCIAMAdapter(config=config)
    assert adapter.health_check() is True


def test_scim_adapter_disabled_provision() -> None:
    config = IAMConfig(enabled=False)
    adapter = SCIMAdapter(config=config)
    user = adapter.provision_user({"id": "user-1"})
    assert user == {}


def test_scim_adapter_enabled_provision() -> None:
    config = IAMConfig(enabled=True)
    adapter = SCIMAdapter(config=config)
    user = adapter.provision_user({"id": "user-1", "email": "a@b.com"})
    assert user["id"] == "user-1"
    assert user["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:User"]


def test_scim_adapter_deprovision_user() -> None:
    config = IAMConfig(enabled=True)
    adapter = SCIMAdapter(config=config)
    adapter.provision_user({"id": "user-1"})
    adapter.deprovision_user("user-1")
    user = adapter.get_users()["user-1"]
    assert user["active"] is False
    assert "lastModified" in user["meta"]


def test_scim_adapter_deprovision_missing_user() -> None:
    config = IAMConfig(enabled=True)
    adapter = SCIMAdapter(config=config)
    adapter.deprovision_user("nonexistent")


def test_scim_adapter_get_users() -> None:
    config = IAMConfig(enabled=True)
    adapter = SCIMAdapter(config=config)
    adapter.provision_user({"id": "user-1"})
    assert "user-1" in adapter.get_users()


def test_scim_adapter_health_check_disabled() -> None:
    config = IAMConfig(enabled=False)
    adapter = SCIMAdapter(config=config)
    assert adapter.health_check() is False


def test_get_iam_adapter_mock() -> None:
    adapter = get_iam_adapter()
    assert isinstance(adapter, MockIAMAdapter)


def test_get_iam_adapter_saml(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.iam_provider = "saml"
    target = "app.infrastructure.integrations.iam_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_iam_adapter()
    assert isinstance(adapter, SAMLIAMAdapter)


def test_get_iam_adapter_oidc(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.iam_provider = "oidc"
    target = "app.infrastructure.integrations.iam_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_iam_adapter()
    assert isinstance(adapter, OIDCIAMAdapter)


def test_get_iam_adapter_scim(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.iam_provider = "scim"
    target = "app.infrastructure.integrations.iam_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_iam_adapter()
    assert isinstance(adapter, SCIMAdapter)


def test_load_iam_config_defaults() -> None:
    config = IAMConfig()
    assert config.enabled is False
    assert config.provider == "mock"
    assert config.entity_id == ""


def test_load_iam_config_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.iam_enabled = True
    settings.iam_provider = "saml"
    settings.saml_entity_id = "entity"
    settings.saml_sso_url = "https://sso"
    settings.saml_x509_cert = "cert"
    settings.oidc_client_id = "client"
    settings.oidc_client_secret = "secret"
    settings.scim_base_url = "https://scim"
    settings.scim_token = "token"
    target = "app.infrastructure.integrations.iam_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    config = _load_iam_config()
    assert config.enabled is True
    assert config.provider == "saml"
    assert config.entity_id == "entity"
