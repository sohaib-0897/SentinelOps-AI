import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sentinelops.domain.models import MetricPoint, now
from sentinelops.providers.gcp.common import client, cloud_call, require_project


class GCPMonitoringMetricsProvider:
    """Cloud Run count/error ratio, server-aligned p95 and resource utilization."""

    def __init__(self, project: str, sdk: Any = None) -> None:
        require_project(project)
        self.project = project
        self.sdk = sdk if sdk is not None else client("google.cloud.monitoring_v3", "MetricServiceClient")

    async def series(self, service_id: str, metric: str, aligner: str) -> list[Any]:
        end = now()
        request = {"name":f"projects/{self.project}", "filter":f'metric.type={json.dumps(metric)} AND resource.type="cloud_run_revision" AND resource.labels.service_name={json.dumps(service_id)}', "interval":{"start_time":{"seconds":int((end-timedelta(minutes=30)).timestamp())}, "end_time":{"seconds":int(end.timestamp())}}, "view":"FULL", "aggregation":{"alignment_period":{"seconds":60}, "per_series_aligner":aligner}}
        return await cloud_call(lambda: list(self.sdk.list_time_series(request=request)))

    async def get_metric_series(self, service_id: str, limit: int = 120) -> list[MetricPoint]:
        if not 1 <= limit <= 600:
            raise ValueError("Metric result limit must be 1–600")
        buckets: dict[int, dict[str, Any]] = defaultdict(lambda: {"requests":0, "errors":0, "available":set(), "revision":"unknown"})
        counts = await self.series(service_id, "run.googleapis.com/request_count", "ALIGN_SUM")
        for series in counts:
            code = str(series.metric.labels.get("response_code", "200"))
            for point in series.points:
                timestamp = int(point.interval.end_time.timestamp())
                bucket = buckets[timestamp]
                count = int(point.value.int64_value)
                bucket["requests"] += count
                bucket["errors"] += count if code.startswith("5") else 0
                bucket["available"].update({"error_rate", "requests"})
                bucket["revision"] = series.resource.labels.get("revision_name", "unknown")
        for name, metric, aligner in [("latency_ms","run.googleapis.com/request_latencies","ALIGN_PERCENTILE_95"), ("cpu","run.googleapis.com/container/cpu/utilizations","ALIGN_PERCENTILE_95"), ("memory","run.googleapis.com/container/memory/utilizations","ALIGN_PERCENTILE_95"), ("db_connections","custom.googleapis.com/sentinelops/db_connections","ALIGN_MEAN")]:
            for series in await self.series(service_id, metric, aligner):
                for point in series.points:
                    timestamp = int(point.interval.end_time.timestamp())
                    bucket = buckets[timestamp]
                    value = float(point.value.double_value)
                    bucket[name] = max(value, bucket.get(name, 0.))
                    bucket["available"].add(name)
        result = []
        for timestamp, bucket in sorted(buckets.items()):
            if not bucket["requests"]:
                continue
            result.append(MetricPoint(timestamp=datetime.fromtimestamp(timestamp, UTC), service_id=service_id, revision=bucket["revision"], requests=bucket["requests"], error_rate=bucket["errors"]/bucket["requests"], latency_ms=bucket.get("latency_ms", 0), cpu=min(1., bucket.get("cpu", 0)), memory=min(1., bucket.get("memory", 0)), db_connections=min(1., bucket.get("db_connections", 0)), available_metrics=sorted(bucket["available"])))
        return result[-limit:]
