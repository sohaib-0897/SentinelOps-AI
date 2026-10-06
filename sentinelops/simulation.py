import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import Field

from sentinelops.domain.models import Deployment, LogEntry, MetricPoint, Model, Service, now
from sentinelops.providers.local import LocalTelemetryProvider


class Scenario(Model):
    name: str
    title: str
    symptoms: list[str]
    metrics: dict[str, float]
    logs: list[str]
    deployment: bool = False
    configuration_changes: dict[str, str] = Field(default_factory=dict)
    expected_root_cause: str | None
    acceptable_evidence: list[str]
    expected_remediation: str | None


def scenarios() -> dict[str, Scenario]:
    path = Path(__file__).resolve().parents[1] / "evals/scenarios/catalog.json"
    return {item["name"]: Scenario.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))}


class SimulationEngine:
    """Seekable virtual clock; safe synthetic telemetry without allocating workload."""

    def __init__(self, telemetry: LocalTelemetryProvider) -> None:
        self.telemetry = telemetry
        self.scenario: Scenario | None = None
        self.step = 0
        self.started_at: datetime = now()
        self.paused = False
        self.speed = 1.0

    def start(self, name: str) -> None:
        self.scenario = scenarios()[name]
        self.step = 0
        self.started_at = now()
        self.paused = False
        self.telemetry.service = Service()
        self.telemetry.metrics = []
        self.telemetry.logs = []
        self.telemetry.deployments = []
        for i in range(8):
            point = self.telemetry.healthy_sample()
            point.timestamp = self.started_at - timedelta(seconds=(8-i)*10)
            self.telemetry.append(point)

    def tick(self) -> dict[str, Any]:
        if not self.scenario or self.paused:
            return {"phase": "paused" if self.paused else "idle"}
        scenario = self.scenario
        timestamp = self.started_at + timedelta(seconds=37 + max(0, self.step - 1)*10)
        if self.step == 0:
            if scenario.deployment or scenario.configuration_changes:
                self.telemetry.service.revision = "api-v2"
                deployment = Deployment(service_id="orders-api", revision="api-v2", previous_revision="api-v1", timestamp=self.started_at, changes=scenario.configuration_changes, healthy=False)
                self.telemetry.deployments.append(deployment)
            self.step += 1
            return {"phase": "deployment", "timestamp": self.started_at.isoformat(), "revision": self.telemetry.service.revision}
        values = {"error_rate": .002, "latency_ms": 85., "cpu": .24, "memory": .38, "db_connections": .22, **scenario.metrics}
        point = MetricPoint.model_validate({"timestamp": timestamp, "revision": self.telemetry.service.revision, **values, "requests": int(values.get("requests", 240))})
        message = scenario.logs[(self.step - 1) % len(scenario.logs)] if scenario.logs else "Request completed successfully"
        entry = LogEntry(timestamp=timestamp, revision=point.revision, severity="ERROR" if scenario.expected_root_cause else "INFO", message=message)
        self.telemetry.append(point, entry)
        self.telemetry.service.healthy = point.error_rate < .05 and point.latency_ms < 800 and point.memory < .9
        self.step += 1
        return {"phase": "degradation" if scenario.expected_root_cause else "healthy", "metric": point.model_dump(mode="json")}

    def recover(self) -> None:
        self.scenario = None
        self.telemetry.service.healthy = True


def materialize(name: str) -> LocalTelemetryProvider:
    provider = LocalTelemetryProvider()
    engine = SimulationEngine(provider)
    engine.start(name)
    for _ in range(7):
        engine.tick()
    return provider
