from datetime import timedelta
from typing import Any

from sentinelops.domain.models import Deployment, LogEntry, MetricPoint, Service, now


class LocalTelemetryProvider:
    def __init__(self) -> None:
        self.service = Service()
        self.metrics: list[MetricPoint] = []
        self.logs: list[LogEntry] = []
        self.deployments: list[Deployment] = []

    def ensure_service(self, service_id: str) -> None:
        if service_id != self.service.id:
            raise ValueError("Unknown service")

    async def search_logs(self, service_id: str, query: str = "", limit: int = 100) -> list[LogEntry]:
        self.ensure_service(service_id)
        return [entry for entry in self.logs if query.lower() in entry.message.lower()][-limit:]

    async def get_metric_series(self, service_id: str, limit: int = 120) -> list[MetricPoint]:
        self.ensure_service(service_id)
        return self.metrics[-limit:]

    async def get_recent_deployments(self, service_id: str) -> list[Deployment]:
        self.ensure_service(service_id)
        return self.deployments[-20:]

    async def get_service_health(self, service_id: str) -> Service:
        self.ensure_service(service_id)
        return self.service.model_copy()

    def snapshot(self) -> dict[str, Any]:
        return {"service": self.service.model_dump(mode="json"), "metrics": [m.model_dump(mode="json") for m in self.metrics], "logs": [entry.model_dump(mode="json") for entry in self.logs], "deployments": [d.model_dump(mode="json") for d in self.deployments]}

    def restore(self, data: dict[str, Any]) -> None:
        self.service = Service.model_validate(data["service"])
        self.metrics = [MetricPoint.model_validate(m) for m in data["metrics"]]
        self.logs = [LogEntry.model_validate(entry) for entry in data["logs"]]
        self.deployments = [Deployment.model_validate(d) for d in data["deployments"]]

    def healthy_sample(self) -> MetricPoint:
        timestamp = max(now(), self.metrics[-1].timestamp + timedelta(seconds=5)) if self.metrics else now()
        return MetricPoint(timestamp=timestamp, revision=self.service.revision, error_rate=.002, latency_ms=85, cpu=.24, memory=.38, db_connections=.22, requests=240)

    def append(self, metric: MetricPoint, log: LogEntry | None = None) -> None:
        self.metrics.append(metric)
        self.metrics = self.metrics[-600:]
        if log:
            self.logs.append(log)
            self.logs = self.logs[-1000:]


class DeterministicLLMProvider:
    async def explain(self, evidence: list[dict[str, Any]]) -> str:
        return "Operational evidence: " + "; ".join(str(e["summary"]) for e in evidence[:6])


class LocalNotificationProvider:
    def __init__(self) -> None:
        self.notifications: list[str] = []

    async def notify(self, incident: Any) -> None:
        self.notifications.append(str(incident.id))
