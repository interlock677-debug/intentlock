from unittest.mock import MagicMock

import pytest

from app.infrastructure.integrations.ticketing_adapter import (
    JiraTicketingAdapter,
    MockTicketingAdapter,
    ServiceNowTicketingAdapter,
    TicketingConfig,
    _load_ticketing_config,
    get_ticketing_adapter,
)


def test_mock_ticketing_adapter_create_ticket() -> None:
    adapter = MockTicketingAdapter()
    ticket = adapter.create_ticket("Bug", "Something broke", severity="high")
    assert ticket["ticket_id"] == "MOCK-0001"
    assert ticket["title"] == "Bug"
    assert ticket["status"] == "open"


def test_mock_ticketing_adapter_update_ticket() -> None:
    adapter = MockTicketingAdapter()
    adapter.create_ticket("Bug", "desc")
    adapter.update_ticket("MOCK-0001", "closed", "fixed")
    ticket = adapter.get_tickets()["MOCK-0001"]
    assert ticket["status"] == "closed"
    assert ticket["last_comment"] == "fixed"


def test_mock_ticketing_adapter_update_ticket_with_comment() -> None:
    adapter = MockTicketingAdapter()
    adapter.create_ticket("Bug", "desc")
    adapter.update_ticket("MOCK-0001", "closed", comment="patched")
    ticket = adapter.get_tickets()["MOCK-0001"]
    assert ticket["last_comment"] == "patched"


def test_mock_ticketing_adapter_update_missing_ticket() -> None:
    adapter = MockTicketingAdapter()
    adapter.update_ticket("MOCK-0001", "closed")


def test_mock_ticketing_adapter_health_check() -> None:
    adapter = MockTicketingAdapter()
    assert adapter.health_check() is True


def test_mock_ticketing_adapter_get_tickets() -> None:
    adapter = MockTicketingAdapter()
    adapter.create_ticket("Bug", "desc")
    assert "MOCK-0001" in adapter.get_tickets()


def test_jira_ticketing_adapter_disabled_create() -> None:
    config = TicketingConfig(enabled=False)
    adapter = JiraTicketingAdapter(config=config)
    ticket = adapter.create_ticket("Bug", "desc")
    assert ticket == {}


def test_jira_ticketing_adapter_enabled_create() -> None:
    config = TicketingConfig(enabled=True)
    adapter = JiraTicketingAdapter(config=config)
    ticket = adapter.create_ticket("Bug", "desc", severity="high")
    assert ticket["ticket_id"] == "INTENTLOCK-001"
    assert ticket["provider"] == "jira"


def test_jira_ticketing_adapter_update_missing_ticket() -> None:
    config = TicketingConfig(enabled=True)
    adapter = JiraTicketingAdapter(config=config)
    adapter.update_ticket("INTENTLOCK-999", "resolved")


def test_jira_ticketing_adapter_update_with_comment() -> None:
    config = TicketingConfig(enabled=True)
    adapter = JiraTicketingAdapter(config=config)
    adapter.create_ticket("Bug", "desc")
    adapter.update_ticket("INTENTLOCK-001", "resolved", "workaround applied")
    ticket = adapter.get_tickets()["INTENTLOCK-001"]
    assert ticket["last_comment"] == "workaround applied"


def test_jira_ticketing_adapter_health_check_disabled() -> None:
    config = TicketingConfig(enabled=False)
    adapter = JiraTicketingAdapter(config=config)
    assert adapter.health_check() is False


def test_jira_ticketing_adapter_get_tickets() -> None:
    config = TicketingConfig(enabled=True)
    adapter = JiraTicketingAdapter(config=config)
    adapter.create_ticket("Bug", "desc")
    assert "INTENTLOCK-001" in adapter.get_tickets()


def test_servicenow_ticketing_adapter_disabled_create() -> None:
    config = TicketingConfig(enabled=False)
    adapter = ServiceNowTicketingAdapter(config=config)
    ticket = adapter.create_ticket("Bug", "desc")
    assert ticket == {}


def test_servicenow_ticketing_adapter_enabled_create() -> None:
    config = TicketingConfig(enabled=True)
    adapter = ServiceNowTicketingAdapter(config=config)
    ticket = adapter.create_ticket("Bug", "desc")
    assert ticket["ticket_id"] == "INC00100000"
    assert ticket["status"] == "New"


def test_servicenow_ticketing_adapter_update_missing_ticket() -> None:
    config = TicketingConfig(enabled=True)
    adapter = ServiceNowTicketingAdapter(config=config)
    adapter.update_ticket("INC99999999", "closed", "fixed")


def test_servicenow_ticketing_adapter_update_with_comment() -> None:
    config = TicketingConfig(enabled=True)
    adapter = ServiceNowTicketingAdapter(config=config)
    adapter.create_ticket("Bug", "desc")
    adapter.update_ticket("INC00100000", "closed", "resolved")
    ticket = adapter.get_tickets()["INC00100000"]
    assert ticket["last_comment"] == "resolved"


def test_servicenow_ticketing_adapter_health_check_disabled() -> None:
    config = TicketingConfig(enabled=False)
    adapter = ServiceNowTicketingAdapter(config=config)
    assert adapter.health_check() is False


def test_servicenow_ticketing_adapter_get_tickets() -> None:
    config = TicketingConfig(enabled=True)
    adapter = ServiceNowTicketingAdapter(config=config)
    adapter.create_ticket("Bug", "desc")
    assert "INC00100000" in adapter.get_tickets()


def test_get_ticketing_adapter_mock() -> None:
    adapter = get_ticketing_adapter()
    assert isinstance(adapter, MockTicketingAdapter)


def test_get_ticketing_adapter_jira(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.ticketing_provider = "jira"
    target = "app.infrastructure.integrations.ticketing_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_ticketing_adapter()
    assert isinstance(adapter, JiraTicketingAdapter)


def test_get_ticketing_adapter_servicenow(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.ticketing_provider = "servicenow"
    target = "app.infrastructure.integrations.ticketing_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_ticketing_adapter()
    assert isinstance(adapter, ServiceNowTicketingAdapter)


def test_load_ticketing_config_defaults() -> None:
    config = TicketingConfig()
    assert config.enabled is False
    assert config.project_key == "INTENTLOCK"


def test_load_ticketing_config_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.ticketing_enabled = True
    settings.ticketing_provider = "jira"
    settings.ticketing_endpoint = "https://jira"
    settings.ticketing_api_key = "key"
    settings.ticketing_project_key = "PROJ"
    settings.ticketing_issue_type = "Task"
    target = "app.infrastructure.integrations.ticketing_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    config = _load_ticketing_config()
    assert config.enabled is True
    assert config.provider == "jira"
    assert config.project_key == "PROJ"
