from types import SimpleNamespace as Obj
from unittest.mock import MagicMock

from sentinelops.domain.models import now
from sentinelops.providers.gcp.monitoring import GCPMonitoringMetricsProvider


async def test_monitoring_aggregates_error_ratio_and_p95() -> None:
    timestamp = now().replace(second=0, microsecond=0)
    def series(code="200", count=100, value=0):
        return Obj(metric=Obj(labels={"response_code":code}), resource=Obj(labels={"revision_name":"api-v2"}), points=[Obj(interval=Obj(end_time=timestamp), value=Obj(int64_value=count, double_value=value))])
    sdk = MagicMock()
    def response(request):
        if "request_count" in request["filter"]:
            return [series(count=82), series(code="500",count=18)]
        if "request_latencies" in request["filter"]:
            assert request["aggregation"]["per_series_aligner"] == "ALIGN_PERCENTILE_95"
            return [series(value=1680)]
        return []
    sdk.list_time_series.side_effect = response
    points = await GCPMonitoringMetricsProvider("test-project",sdk).get_metric_series("orders-api")
    assert points[0].error_rate == .18
    assert points[0].latency_ms == 1680
    assert "db_connections" not in points[0].available_metrics
    assert points[0].requests == 100
