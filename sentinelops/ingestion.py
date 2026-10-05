from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from sentinelops.detection import detect_incident
from sentinelops.domain.models import Deployment, LogEntry, MetricPoint, Model, Service
from sentinelops.runtime import Runtime


class TelemetryBatch(Model):
    service_id: Literal["orders-api"] = "orders-api"
    metrics: list[MetricPoint] = Field(default_factory=list, max_length=600)
    logs: list[LogEntry] = Field(default_factory=list, max_length=200)
    deployments: list[Deployment] = Field(default_factory=list, max_length=20)
    service: Service | None = None

    @field_validator("metrics", "logs", "deployments")
    @classmethod
    def scoped_records(cls, records: list[Any]) -> list[Any]:
        for record in records:
            if record.service_id != "orders-api":
                raise ValueError("Telemetry must belong to the allow-listed service")
            if record.timestamp.tzinfo is None:
                raise ValueError("Telemetry timestamps must include a timezone")
        return records

    @field_validator("service")
    @classmethod
    def scoped_service(cls, service: Service | None) -> Service | None:
        if service and service.id != "orders-api":
            raise ValueError("Unknown service")
        return service


async def ingest(runtime: Runtime, batch: TelemetryBatch) -> dict[str, Any]:
    """Accept ordered, authenticated observations without executing remediation."""
    async with runtime.control_lock:
        telemetry = runtime.telemetry
        latest: datetime | None = telemetry.metrics[-1].timestamp if telemetry.metrics else None
        fresh = [p for p in sorted(batch.metrics, key=lambda p: p.timestamp) if latest is None or p.timestamp > latest]
        seen: set[datetime] = set()
        for point in fresh:
            if point.timestamp not in seen:
                telemetry.append(point)
                seen.add(point.timestamp)
        log_ids = {entry.id for entry in telemetry.logs}
        telemetry.logs = [*telemetry.logs, *(entry for entry in batch.logs if entry.id not in log_ids)][-1000:]
        deployment_ids = {entry.id for entry in telemetry.deployments}
        telemetry.deployments = sorted([*telemetry.deployments, *(entry for entry in batch.deployments if entry.id not in deployment_ids)], key=lambda entry: entry.timestamp)[-20:]
        if batch.service:
            telemetry.service = batch.service
        await runtime.repository.set_runtime("telemetry", telemetry.snapshot())
        incident = detect_incident(telemetry.metrics, await runtime.repository.list_incidents(limit=1000)) if seen else None
        if incident:
            await runtime.workflow.persist(incident, "IncidentDetected")
            runtime.launch_investigation(incident.id)
        if seen:
            await runtime.bus.publish({"type":"metrics", "data":{"accepted":len(seen)}})
        return {"accepted_metrics":len(seen), "incident_id":incident.id if incident else None}
