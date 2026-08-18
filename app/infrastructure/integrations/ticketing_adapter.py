import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TicketingConfig:
    enabled: bool = False
    provider: str = "mock"
    endpoint: str = ""
    api_key: str = ""
    project_key: str = "INTENTLOCK"
    issue_type: str = "Security Incident"


class TicketingAdapter(ABC):
    """Port for ticketing system integration."""

    @abstractmethod
    def create_ticket(
        self,
        title: str,
        description: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Create a ticket in the ticketing system."""

    @abstractmethod
    def update_ticket(
        self,
        ticket_id: str,
        status: str,
        comment: str = "",
    ) -> None:
        """Update an existing ticket."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the ticketing system is reachable."""


class MockTicketingAdapter(TicketingAdapter):
    """Mock ticketing adapter for testing and development."""

    def __init__(self, config: TicketingConfig | None = None) -> None:
        self._config = config or TicketingConfig()
        self._tickets: dict[str, dict[str, Any]] = {}

    def create_ticket(
        self,
        title: str,
        description: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        ticket_id = f"MOCK-{len(self._tickets) + 1:04d}"
        ticket = {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "severity": severity,
            "status": "open",
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
        self._tickets[ticket_id] = ticket
        logger.debug("Mock ticket created: %s", ticket_id)
        return ticket

    def update_ticket(
        self,
        ticket_id: str,
        status: str,
        comment: str = "",
    ) -> None:
        if ticket_id in self._tickets:
            self._tickets[ticket_id]["status"] = status
            self._tickets[ticket_id]["updated_at"] = datetime.now(tz=UTC).isoformat()
            if comment:
                self._tickets[ticket_id]["last_comment"] = comment
            logger.debug("Mock ticket updated: %s -> %s", ticket_id, status)

    def health_check(self) -> bool:
        return True

    def get_tickets(self) -> dict[str, dict[str, Any]]:
        return dict(self._tickets)


class JiraTicketingAdapter(TicketingAdapter):
    """Jira ticketing adapter."""

    def __init__(self, config: TicketingConfig | None = None) -> None:
        self._config = config or _load_ticketing_config()
        self._tickets: dict[str, dict[str, Any]] = {}

    def create_ticket(
        self,
        title: str,
        description: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        if not self._config.enabled:
            return {}
        ticket_id = f"{self._config.project_key}-{len(self._tickets) + 1:03d}"
        ticket = {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "severity": severity,
            "status": "open",
            "provider": "jira",
            "project": self._config.project_key,
            "issue_type": self._config.issue_type,
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
        self._tickets[ticket_id] = ticket
        logger.debug("Jira ticket created: %s", ticket_id)
        return ticket

    def update_ticket(
        self,
        ticket_id: str,
        status: str,
        comment: str = "",
    ) -> None:
        if ticket_id in self._tickets:
            self._tickets[ticket_id]["status"] = status
            self._tickets[ticket_id]["updated_at"] = datetime.now(tz=UTC).isoformat()
            if comment:
                self._tickets[ticket_id]["last_comment"] = comment
            logger.debug("Jira ticket updated: %s -> %s", ticket_id, status)

    def health_check(self) -> bool:
        return self._config.enabled

    def get_tickets(self) -> dict[str, dict[str, Any]]:
        return dict(self._tickets)


class ServiceNowTicketingAdapter(TicketingAdapter):
    """ServiceNow ticketing adapter."""

    def __init__(self, config: TicketingConfig | None = None) -> None:
        self._config = config or _load_ticketing_config()
        self._tickets: dict[str, dict[str, Any]] = {}

    def create_ticket(
        self,
        title: str,
        description: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        if not self._config.enabled:
            return {}
        ticket_id = f"INC{len(self._tickets) + 100000:08d}"
        ticket = {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "severity": severity,
            "status": "New",
            "provider": "servicenow",
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
        self._tickets[ticket_id] = ticket
        logger.debug("ServiceNow ticket created: %s", ticket_id)
        return ticket

    def update_ticket(
        self,
        ticket_id: str,
        status: str,
        comment: str = "",
    ) -> None:
        if ticket_id in self._tickets:
            self._tickets[ticket_id]["status"] = status
            self._tickets[ticket_id]["updated_at"] = datetime.now(tz=UTC).isoformat()
            if comment:
                self._tickets[ticket_id]["last_comment"] = comment
            logger.debug("ServiceNow ticket updated: %s -> %s", ticket_id, status)

    def health_check(self) -> bool:
        return self._config.enabled

    def get_tickets(self) -> dict[str, dict[str, Any]]:
        return dict(self._tickets)


def get_ticketing_adapter() -> TicketingAdapter:
    settings = get_settings()
    provider = getattr(settings, "ticketing_provider", "mock")
    if provider == "jira":
        return JiraTicketingAdapter()
    if provider == "servicenow":
        return ServiceNowTicketingAdapter()
    return MockTicketingAdapter()


def _load_ticketing_config() -> TicketingConfig:
    settings = get_settings()
    return TicketingConfig(
        enabled=getattr(settings, "ticketing_enabled", False),
        provider=getattr(settings, "ticketing_provider", "mock"),
        endpoint=getattr(settings, "ticketing_endpoint", ""),
        api_key=getattr(settings, "ticketing_api_key", ""),
        project_key=getattr(settings, "ticketing_project_key", "INTENTLOCK"),
        issue_type=getattr(settings, "ticketing_issue_type", "Security Incident"),
    )
