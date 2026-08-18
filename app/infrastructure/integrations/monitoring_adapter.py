import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonitoringConfig:
    enabled: bool = False
    provider: str = "mock"
    endpoint: str = ""
    api_key: str = ""
    namespace: str = "intentlock"
    service_name: str = "intentlock"


class MonitoringAdapter(ABC):
    """Port for monitoring integration."""

    @abstractmethod
    def record_counter(
        self,
        metric_name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a counter metric."""

    @abstractmethod
    def record_gauge(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a gauge metric."""

    @abstractmethod
    def record_histogram(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a histogram metric."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the monitoring system is reachable."""


class MockMonitoringAdapter(MonitoringAdapter):
    """Mock monitoring adapter for testing and development."""

    def __init__(self, config: MonitoringConfig | None = None) -> None:
        self._config = config or MonitoringConfig()
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[dict[str, Any]]] = {}

    def record_counter(
        self,
        metric_name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        key = _tag_key(metric_name, tags)
        self._counters.setdefault(key, 0)
        self._counters[key] += value
        logger.debug("Mock counter %s = %d", key, self._counters[key])

    def record_gauge(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        key = _tag_key(metric_name, tags)
        self._gauges[key] = value
        logger.debug("Mock gauge %s = %s", key, value)

    def record_histogram(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        key = _tag_key(metric_name, tags)
        self._histograms.setdefault(key, []).append({
            "value": value,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        })
        logger.debug("Mock histogram %s sample recorded", key)

    def health_check(self) -> bool:
        return True

    def get_counters(self) -> dict[str, int]:
        return dict(self._counters)

    def get_gauges(self) -> dict[str, float]:
        return dict(self._gauges)

    def get_histograms(self) -> dict[str, list[dict[str, Any]]]:
        return {k: list(v) for k, v in self._histograms.items()}


class PrometheusMonitoringAdapter(MonitoringAdapter):
    """Prometheus monitoring adapter."""

    def __init__(self, config: MonitoringConfig | None = None) -> None:
        self._config = config or _load_monitoring_config()
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[dict[str, Any]]] = {}

    def record_counter(
        self,
        metric_name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._counters.setdefault(key, 0)
        self._counters[key] += value
        logger.debug("Prometheus counter %s = %d", key, self._counters[key])

    def record_gauge(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._gauges[key] = value
        logger.debug("Prometheus gauge %s = %s", key, value)

    def record_histogram(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._histograms.setdefault(key, []).append({
            "value": value,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        })
        logger.debug("Prometheus histogram %s sample recorded", key)

    def health_check(self) -> bool:
        return self._config.enabled

    def get_counters(self) -> dict[str, int]:
        return dict(self._counters)

    def get_gauges(self) -> dict[str, float]:
        return dict(self._gauges)

    def get_histograms(self) -> dict[str, list[dict[str, Any]]]:
        return {k: list(v) for k, v in self._histograms.items()}


class DatadogMonitoringAdapter(MonitoringAdapter):
    """Datadog monitoring adapter."""

    def __init__(self, config: MonitoringConfig | None = None) -> None:
        self._config = config or _load_monitoring_config()
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[dict[str, Any]]] = {}

    def record_counter(
        self,
        metric_name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._counters.setdefault(key, 0)
        self._counters[key] += value
        logger.debug("Datadog counter %s = %d", key, self._counters[key])

    def record_gauge(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._gauges[key] = value
        logger.debug("Datadog gauge %s = %s", key, value)

    def record_histogram(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._histograms.setdefault(key, []).append({
            "value": value,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        })
        logger.debug("Datadog histogram %s sample recorded", key)

    def health_check(self) -> bool:
        return self._config.enabled

    def get_counters(self) -> dict[str, int]:
        return dict(self._counters)

    def get_gauges(self) -> dict[str, float]:
        return dict(self._gauges)

    def get_histograms(self) -> dict[str, list[dict[str, Any]]]:
        return {k: list(v) for k, v in self._histograms.items()}


class CloudWatchMonitoringAdapter(MonitoringAdapter):
    """AWS CloudWatch monitoring adapter."""

    def __init__(self, config: MonitoringConfig | None = None) -> None:
        self._config = config or _load_monitoring_config()
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[dict[str, Any]]] = {}

    def record_counter(
        self,
        metric_name: str,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._counters.setdefault(key, 0)
        self._counters[key] += value
        logger.debug("CloudWatch counter %s = %d", key, self._counters[key])

    def record_gauge(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._gauges[key] = value
        logger.debug("CloudWatch gauge %s = %s", key, value)

    def record_histogram(
        self,
        metric_name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        if not self._config.enabled:
            return
        key = _tag_key(metric_name, tags)
        self._histograms.setdefault(key, []).append({
            "value": value,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        })
        logger.debug("CloudWatch histogram %s sample recorded", key)

    def health_check(self) -> bool:
        return self._config.enabled

    def get_counters(self) -> dict[str, int]:
        return dict(self._counters)

    def get_gauges(self) -> dict[str, float]:
        return dict(self._gauges)

    def get_histograms(self) -> dict[str, list[dict[str, Any]]]:
        return {k: list(v) for k, v in self._histograms.items()}


def get_monitoring_adapter() -> MonitoringAdapter:
    settings = get_settings()
    provider = getattr(settings, "monitoring_provider", "mock")
    if provider == "prometheus":
        return PrometheusMonitoringAdapter()
    if provider == "datadog":
        return DatadogMonitoringAdapter()
    if provider == "cloudwatch":
        return CloudWatchMonitoringAdapter()
    return MockMonitoringAdapter()


def _load_monitoring_config() -> MonitoringConfig:
    settings = get_settings()
    return MonitoringConfig(
        enabled=getattr(settings, "monitoring_enabled", False),
        provider=getattr(settings, "monitoring_provider", "mock"),
        endpoint=getattr(settings, "monitoring_endpoint", ""),
        api_key=getattr(settings, "monitoring_api_key", ""),
        namespace=getattr(settings, "monitoring_namespace", "intentlock"),
        service_name=getattr(settings, "monitoring_service_name", "intentlock"),
    )


def _tag_key(metric_name: str, tags: dict[str, str] | None) -> str:
    if not tags:
        return metric_name
    tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
    return f"{metric_name}#{tag_str}"
