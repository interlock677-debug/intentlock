from unittest.mock import MagicMock

import pytest

from app.infrastructure.integrations.monitoring_adapter import (
    CloudWatchMonitoringAdapter,
    DatadogMonitoringAdapter,
    MockMonitoringAdapter,
    MonitoringConfig,
    PrometheusMonitoringAdapter,
    _load_monitoring_config,
    get_monitoring_adapter,
)


def test_mock_monitoring_adapter_record_counter() -> None:
    adapter = MockMonitoringAdapter()
    adapter.record_counter("requests", value=5, tags={"env": "prod"})
    assert adapter.get_counters()["requests#env=prod"] == 5


def test_mock_monitoring_adapter_record_gauge() -> None:
    adapter = MockMonitoringAdapter()
    adapter.record_gauge("temperature", value=98.6, tags={"sensor": "1"})
    assert adapter.get_gauges()["temperature#sensor=1"] == 98.6


def test_mock_monitoring_adapter_record_histogram() -> None:
    adapter = MockMonitoringAdapter()
    adapter.record_histogram("latency", value=0.05)
    hist = adapter.get_histograms()["latency"]
    assert len(hist) == 1
    assert hist[0]["value"] == 0.05


def test_mock_monitoring_adapter_health_check() -> None:
    adapter = MockMonitoringAdapter()
    assert adapter.health_check() is True


def test_mock_monitoring_adapter_get_counters() -> None:
    adapter = MockMonitoringAdapter()
    adapter.record_counter("requests")
    assert adapter.get_counters()["requests"] == 1


def test_mock_monitoring_adapter_get_histograms() -> None:
    adapter = MockMonitoringAdapter()
    adapter.record_histogram("latency", 0.1)
    assert "latency" in adapter.get_histograms()


def test_prometheus_adapter_disabled_does_not_record() -> None:
    config = MonitoringConfig(enabled=False)
    adapter = PrometheusMonitoringAdapter(config=config)
    adapter.record_counter("requests")
    adapter.record_gauge("temp", 10.0)
    adapter.record_histogram("latency", 0.1)
    assert adapter.get_counters() == {}
    assert adapter.get_gauges() == {}
    assert adapter.get_histograms() == {}


def test_prometheus_adapter_enabled_counter() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = PrometheusMonitoringAdapter(config=config)
    adapter.record_counter("requests")
    assert adapter.get_counters()["requests"] == 1


def test_prometheus_adapter_enabled_gauge() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = PrometheusMonitoringAdapter(config=config)
    adapter.record_gauge("cpu", 55.5)
    assert adapter.get_gauges()["cpu"] == 55.5


def test_prometheus_adapter_enabled_histogram() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = PrometheusMonitoringAdapter(config=config)
    adapter.record_histogram("duration", 0.2)
    assert len(adapter.get_histograms()["duration"]) == 1


def test_prometheus_adapter_health_check_disabled() -> None:
    config = MonitoringConfig(enabled=False)
    adapter = PrometheusMonitoringAdapter(config=config)
    assert adapter.health_check() is False


def test_prometheus_adapter_get_counters() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = PrometheusMonitoringAdapter(config=config)
    adapter.record_counter("requests", value=3)
    assert adapter.get_counters()["requests"] == 3


def test_prometheus_adapter_get_histograms() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = PrometheusMonitoringAdapter(config=config)
    adapter.record_histogram("latency", 0.1)
    assert "latency" in adapter.get_histograms()


def test_datadog_adapter_enabled_counter() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = DatadogMonitoringAdapter(config=config)
    adapter.record_counter("requests")
    assert adapter.get_counters()["requests"] == 1


def test_datadog_adapter_enabled_gauge() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = DatadogMonitoringAdapter(config=config)
    adapter.record_gauge("cpu", 55.5)
    assert adapter.get_gauges()["cpu"] == 55.5


def test_datadog_adapter_enabled_histogram() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = DatadogMonitoringAdapter(config=config)
    adapter.record_histogram("duration", 0.2)
    assert len(adapter.get_histograms()["duration"]) == 1


def test_datadog_adapter_disabled_does_not_record() -> None:
    config = MonitoringConfig(enabled=False)
    adapter = DatadogMonitoringAdapter(config=config)
    adapter.record_counter("requests")
    adapter.record_gauge("temp", 10.0)
    adapter.record_histogram("latency", 0.1)
    assert adapter.get_counters() == {}
    assert adapter.get_gauges() == {}
    assert adapter.get_histograms() == {}


def test_datadog_adapter_health_check_disabled() -> None:
    config = MonitoringConfig(enabled=False)
    adapter = DatadogMonitoringAdapter(config=config)
    assert adapter.health_check() is False


def test_datadog_adapter_get_counters() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = DatadogMonitoringAdapter(config=config)
    adapter.record_counter("requests", value=2)
    assert adapter.get_counters()["requests"] == 2


def test_datadog_adapter_get_histograms() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = DatadogMonitoringAdapter(config=config)
    adapter.record_histogram("latency", 0.1)
    assert "latency" in adapter.get_histograms()


def test_cloudwatch_adapter_enabled_counter() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = CloudWatchMonitoringAdapter(config=config)
    adapter.record_counter("requests")
    assert adapter.get_counters()["requests"] == 1


def test_cloudwatch_adapter_enabled_gauge() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = CloudWatchMonitoringAdapter(config=config)
    adapter.record_gauge("cpu", 55.5)
    assert adapter.get_gauges()["cpu"] == 55.5


def test_cloudwatch_adapter_enabled_histogram() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = CloudWatchMonitoringAdapter(config=config)
    adapter.record_histogram("duration", 0.2)
    assert len(adapter.get_histograms()["duration"]) == 1


def test_cloudwatch_adapter_disabled_does_not_record() -> None:
    config = MonitoringConfig(enabled=False)
    adapter = CloudWatchMonitoringAdapter(config=config)
    adapter.record_counter("requests")
    adapter.record_gauge("temp", 10.0)
    adapter.record_histogram("latency", 0.1)
    assert adapter.get_counters() == {}
    assert adapter.get_gauges() == {}
    assert adapter.get_histograms() == {}


def test_cloudwatch_adapter_health_check_disabled() -> None:
    config = MonitoringConfig(enabled=False)
    adapter = CloudWatchMonitoringAdapter(config=config)
    assert adapter.health_check() is False


def test_cloudwatch_adapter_get_counters() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = CloudWatchMonitoringAdapter(config=config)
    adapter.record_counter("requests", value=3)
    assert adapter.get_counters()["requests"] == 3


def test_cloudwatch_adapter_get_histograms() -> None:
    config = MonitoringConfig(enabled=True)
    adapter = CloudWatchMonitoringAdapter(config=config)
    adapter.record_histogram("latency", 0.1)
    assert "latency" in adapter.get_histograms()


def test_get_monitoring_adapter_mock() -> None:
    adapter = get_monitoring_adapter()
    assert isinstance(adapter, MockMonitoringAdapter)


def test_get_monitoring_adapter_prometheus(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.monitoring_provider = "prometheus"
    target = "app.infrastructure.integrations.monitoring_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_monitoring_adapter()
    assert isinstance(adapter, PrometheusMonitoringAdapter)


def test_get_monitoring_adapter_datadog(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.monitoring_provider = "datadog"
    target = "app.infrastructure.integrations.monitoring_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_monitoring_adapter()
    assert isinstance(adapter, DatadogMonitoringAdapter)


def test_get_monitoring_adapter_cloudwatch(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.monitoring_provider = "cloudwatch"
    target = "app.infrastructure.integrations.monitoring_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    adapter = get_monitoring_adapter()
    assert isinstance(adapter, CloudWatchMonitoringAdapter)


def test_load_monitoring_config_defaults() -> None:
    config = MonitoringConfig()
    assert config.enabled is False
    assert config.provider == "mock"
    assert config.namespace == "intentlock"


def test_load_monitoring_config_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.monitoring_enabled = True
    settings.monitoring_provider = "datadog"
    settings.monitoring_endpoint = "https://datadog"
    settings.monitoring_api_key = "key"
    settings.monitoring_namespace = "ns"
    settings.monitoring_service_name = "svc"
    target = "app.infrastructure.integrations.monitoring_adapter.get_settings"
    monkeypatch.setattr(target, lambda: settings)
    config = _load_monitoring_config()
    assert config.enabled is True
    assert config.provider == "datadog"
    assert config.endpoint == "https://datadog"
