from typing import Any, Protocol

from sentinelops.domain.models import (
    AuditEvent,
    Deployment,
    HistoricalIncident,
    Incident,
    LogEntry,
    MetricPoint,
    RemediationAction,
    Service,
)


class LogProvider(Protocol):
    async def search_logs(self, service_id: str, query: str = "", limit: int = 100) -> list[LogEntry]: ...


class MetricsProvider(Protocol):
    async def get_metric_series(self, service_id: str, limit: int = 120) -> list[MetricPoint]: ...


class DeploymentProvider(Protocol):
    async def get_recent_deployments(self, service_id: str) -> list[Deployment]: ...
    async def get_service_health(self, service_id: str) -> Service: ...


class TelemetryProvider(LogProvider, MetricsProvider, DeploymentProvider, Protocol):
    pass


class IncidentRepository(Protocol):
    async def get(self, incident_id: str) -> Incident | None: ...
    async def list_incidents(self, limit: int = 100, offset: int = 0) -> list[Incident]: ...
    async def save(self, incident: Incident, audit: list[AuditEvent] | None = None) -> None: ...


class VectorSearchProvider(Protocol):
    async def search(self, query: str, limit: int = 3) -> list[HistoricalIncident]: ...


class LLMProvider(Protocol):
    async def explain(self, evidence: list[dict[str, Any]]) -> str: ...


class RemediationProvider(Protocol):
    async def execute(self, action: RemediationAction) -> dict[str, Any]: ...


class EventBus(Protocol):
    async def publish(self, event: dict[str, Any]) -> None: ...


class NotificationProvider(Protocol):
    async def notify(self, incident: Incident) -> None: ...
