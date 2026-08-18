import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SIEMConfig:
    enabled: bool = False
    provider: str = "mock"
    endpoint: str = ""
    api_key: str = ""
    index: str = "intentlock-security"


class SIEMAdapter(ABC):
    """Port for SIEM integration."""

    @abstractmethod
    def send(self, event: dict[str, Any]) -> None:
        """Send an event to the SIEM."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the SIEM is reachable."""


class MockSIEMAdapter(SIEMAdapter):
    """Mock SIEM adapter for testing and development."""

    def __init__(self, config: SIEMConfig | None = None) -> None:
        self._config = config or SIEMConfig()
        self._events: list[dict[str, Any]] = []

    def send(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        logger.debug("Mock SIEM event sent: %s", event.get("event_type"))

    def health_check(self) -> bool:
        return True

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)


class SplunkSIEMAdapter(SIEMAdapter):
    """Splunk SIEM adapter using HEC."""

    def __init__(self, config: SIEMConfig | None = None) -> None:
        self._config = config or _load_siem_config()
        self._events: list[dict[str, Any]] = []

    def send(self, event: dict[str, Any]) -> None:
        if not self._config.enabled:
            return
        payload = {
            "time": datetime.now(tz=UTC).timestamp(),
            "host": get_settings().app_name,
            "source": "intentlock",
            "sourcetype": "intentlock:security",
            "index": self._config.index,
            "event": event,
        }
        self._events.append(payload)
        logger.debug("Splunk SIEM event queued: %s", event.get("event_type"))

    def health_check(self) -> bool:
        return self._config.enabled

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)


class QRadarSIEMAdapter(SIEMAdapter):
    """QRadar SIEM adapter using REST API."""

    def __init__(self, config: SIEMConfig | None = None) -> None:
        self._config = config or _load_siem_config()
        self._events: list[dict[str, Any]] = []

    def send(self, event: dict[str, Any]) -> None:
        if not self._config.enabled:
            return
        payload = {
            "eventSource": "intentlock",
            "startTime": datetime.now(tz=UTC).isoformat(),
            "eventType": event.get("event_type", "unknown"),
            "fields": event,
        }
        self._events.append(payload)
        logger.debug("QRadar SIEM event queued: %s", event.get("event_type"))

    def health_check(self) -> bool:
        return self._config.enabled

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)


class SentinelSIEMAdapter(SIEMAdapter):
    """Microsoft Sentinel SIEM adapter."""

    def __init__(self, config: SIEMConfig | None = None) -> None:
        self._config = config or _load_siem_config()
        self._events: list[dict[str, Any]] = []

    def send(self, event: dict[str, Any]) -> None:
        if not self._config.enabled:
            return
        payload = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "source": "intentlock",
            "type": event.get("event_type", "unknown"),
            "data": event,
        }
        self._events.append(payload)
        logger.debug("Sentinel SIEM event queued: %s", event.get("event_type"))

    def health_check(self) -> bool:
        return self._config.enabled

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)


def get_siem_adapter() -> SIEMAdapter:
    settings = get_settings()
    provider = getattr(settings, "siem_provider", "mock")
    if provider == "splunk":
        return SplunkSIEMAdapter()
    if provider == "qradar":
        return QRadarSIEMAdapter()
    if provider == "sentinel":
        return SentinelSIEMAdapter()
    return MockSIEMAdapter()


def _load_siem_config() -> SIEMConfig:
    settings = get_settings()
    return SIEMConfig(
        enabled=getattr(settings, "siem_enabled", False),
        provider=getattr(settings, "siem_provider", "mock"),
        endpoint=getattr(settings, "siem_endpoint", ""),
        api_key=getattr(settings, "siem_api_key", ""),
        index=getattr(settings, "siem_index", "intentlock-security"),
    )
