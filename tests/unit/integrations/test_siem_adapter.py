from unittest.mock import MagicMock

import pytest

from app.infrastructure.integrations.siem_adapter import (
    MockSIEMAdapter,
    QRadarSIEMAdapter,
    SentinelSIEMAdapter,
    SIEMConfig,
    SplunkSIEMAdapter,
    _load_siem_config,
    get_siem_adapter,
)


def test_mock_siem_adapter_send() -> None:
    adapter = MockSIEMAdapter()
    adapter.send({"event_type": "test"})
    assert len(adapter.get_events()) == 1
    assert adapter.get_events()[0]["event_type"] == "test"


def test_mock_siem_adapter_health_check() -> None:
    adapter = MockSIEMAdapter()
    assert adapter.health_check() is True


def test_splunk_siem_adapter_disabled_send() -> None:
    config = SIEMConfig(enabled=False)
    adapter = SplunkSIEMAdapter(config=config)
    adapter.send({"event_type": "test"})
    assert adapter.get_events() == []


def test_splunk_siem_adapter_enabled_send() -> None:
    config = SIEMConfig(enabled=True)
    adapter = SplunkSIEMAdapter(config=config)
    adapter.send({"event_type": "test"})
    events = adapter.get_events()
    assert len(events) == 1
    assert events[0]["event"]["event_type"] == "test"
    assert events[0]["source"] == "intentlock"


def test_splunk_siem_adapter_health_check_disabled() -> None:
    config = SIEMConfig(enabled=False)
    adapter = SplunkSIEMAdapter(config=config)
    assert adapter.health_check() is False


def test_qradar_siem_adapter_disabled_send() -> None:
    config = SIEMConfig(enabled=False)
    adapter = QRadarSIEMAdapter(config=config)
    adapter.send({"event_type": "test"})
    assert adapter.get_events() == []


def test_qradar_siem_adapter_enabled_send() -> None:
    config = SIEMConfig(enabled=True)
    adapter = QRadarSIEMAdapter(config=config)
    adapter.send({"event_type": "test"})
    events = adapter.get_events()
    assert len(events) == 1
    assert events[0]["eventType"] == "test"


def test_qradar_siem_adapter_health_check_disabled() -> None:
    config = SIEMConfig(enabled=False)
    adapter = QRadarSIEMAdapter(config=config)
    assert adapter.health_check() is False


def test_sentinel_siem_adapter_disabled_send() -> None:
    config = SIEMConfig(enabled=False)
    adapter = SentinelSIEMAdapter(config=config)
    adapter.send({"event_type": "test"})
    assert adapter.get_events() == []


def test_sentinel_siem_adapter_enabled_send() -> None:
    config = SIEMConfig(enabled=True)
    adapter = SentinelSIEMAdapter(config=config)
    adapter.send({"event_type": "test"})
    events = adapter.get_events()
    assert len(events) == 1
    assert events[0]["type"] == "test"


def test_sentinel_siem_adapter_health_check_disabled() -> None:
    config = SIEMConfig(enabled=False)
    adapter = SentinelSIEMAdapter(config=config)
    assert adapter.health_check() is False


def test_get_siem_adapter_mock() -> None:
    adapter = get_siem_adapter()
    assert isinstance(adapter, MockSIEMAdapter)


def test_get_siem_adapter_splunk(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.siem_provider = "splunk"
    target = "app.infrastructure.integrations.siem_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_siem_adapter()
    assert isinstance(adapter, SplunkSIEMAdapter)


def test_get_siem_adapter_qradar(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.siem_provider = "qradar"
    target = "app.infrastructure.integrations.siem_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_siem_adapter()
    assert isinstance(adapter, QRadarSIEMAdapter)


def test_get_siem_adapter_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.siem_provider = "sentinel"
    target = "app.infrastructure.integrations.siem_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_siem_adapter()
    assert isinstance(adapter, SentinelSIEMAdapter)


def test_load_siem_config_defaults() -> None:
    config = SIEMConfig()
    assert config.enabled is False
    assert config.provider == "mock"
    assert config.index == "intentlock-security"


def test_load_siem_config_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.siem_enabled = True
    settings.siem_provider = "splunk"
    settings.siem_endpoint = "https://splunk"
    settings.siem_api_key = "key"
    settings.siem_index = "security"
    target = "app.infrastructure.integrations.siem_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    config = _load_siem_config()
    assert config.enabled is True
    assert config.provider == "splunk"
    assert config.endpoint == "https://splunk"
