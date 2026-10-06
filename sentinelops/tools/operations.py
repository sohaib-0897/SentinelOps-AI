from pathlib import Path

from pydantic import Field

from sentinelops.domain.models import (
    Deployment,
    HistoricalIncident,
    LogEntry,
    MetricPoint,
    Model,
    Service,
)
from sentinelops.providers.contracts import (
    DeploymentProvider,
    LogProvider,
    MetricsProvider,
    VectorSearchProvider,
)


class ServiceQuery(Model):
    service_id: str = Field(default="orders-api", pattern=r"^[a-z][a-z0-9-]{0,62}$")
    query: str = Field(default="", max_length=512)
    limit: int = Field(default=100, ge=1, le=600)


class AgentTools:
    READ_CAPABILITIES = frozenset({"search_logs", "get_error_rate", "get_latency", "get_metric_series", "get_recent_deployments", "get_revision_details", "compare_revisions", "get_service_health", "search_historical_incidents", "retrieve_runbook"})

    def __init__(self, logs: LogProvider, metrics: MetricsProvider, deployments: DeploymentProvider, vectors: VectorSearchProvider) -> None:
        self.logs = logs
        self.metrics = metrics
        self.deployments = deployments
        self.vectors = vectors
        self.calls: list[str] = []

    async def search_logs(self, request: ServiceQuery) -> list[LogEntry]:
        self.calls.append("search_logs")
        return await self.logs.search_logs(request.service_id, request.query, request.limit)

    async def get_metric_series(self, request: ServiceQuery) -> list[MetricPoint]:
        self.calls.append("get_metric_series")
        return await self.metrics.get_metric_series(request.service_id, request.limit)

    async def get_error_rate(self, request: ServiceQuery) -> float:
        self.calls.append("get_error_rate")
        points = await self.metrics.get_metric_series(request.service_id, 1)
        return points[-1].error_rate if points else 0

    async def get_latency(self, request: ServiceQuery) -> float:
        self.calls.append("get_latency")
        points = await self.metrics.get_metric_series(request.service_id, 1)
        return points[-1].latency_ms if points else 0

    async def get_recent_deployments(self, request: ServiceQuery) -> list[Deployment]:
        self.calls.append("get_recent_deployments")
        return await self.deployments.get_recent_deployments(request.service_id)

    async def get_revision_details(self, request: ServiceQuery, revision: str) -> Deployment | None:
        self.calls.append("get_revision_details")
        return next((d for d in await self.deployments.get_recent_deployments(request.service_id) if d.revision == revision), None)

    async def compare_revisions(self, request: ServiceQuery) -> dict[str, str]:
        self.calls.append("compare_revisions")
        deployments = await self.deployments.get_recent_deployments(request.service_id)
        return deployments[-1].changes if deployments else {}

    async def get_service_health(self, request: ServiceQuery) -> Service:
        self.calls.append("get_service_health")
        return await self.deployments.get_service_health(request.service_id)

    async def search_historical_incidents(self, request: ServiceQuery) -> list[HistoricalIncident]:
        self.calls.append("search_historical_incidents")
        return await self.vectors.search(request.query, min(request.limit, 10))

    async def retrieve_runbook(self, cause: str) -> str:
        self.calls.append("retrieve_runbook")
        allowed = {"bad_deployment": "rollback.md", "database_exhaustion": "database.md", "memory_regression": "rollback.md", "configuration_regression": "rollback.md"}
        filename = allowed.get(cause, "general.md")
        return (Path(__file__).resolve().parents[2] / "runbooks" / filename).read_text(encoding="utf-8")
