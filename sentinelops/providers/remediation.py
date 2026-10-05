from typing import Any

import httpx

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import LogEntry, RemediationAction
from sentinelops.providers.local import LocalTelemetryProvider
from sentinelops.security.approval import validate_action


class LocalRemediationProvider:
    def __init__(self, telemetry: LocalTelemetryProvider, demo_url: str | None = None, operator_token: str = "") -> None:
        self.telemetry = telemetry
        self.demo_url = demo_url
        self.operator_token = operator_token

    async def execute(self, action: RemediationAction) -> dict[str, Any]:
        validate_action(action, self.telemetry.service.id)
        if action.capability in {"rollback_demo_revision", "change_demo_traffic_split"}:
            expected = action.parameters["expected_revision"]
            revision = action.parameters["revision"]
            if self.telemetry.service.revision != expected:
                raise ConflictError("Service revision changed since plan creation")
            if not any(d.revision == expected and d.previous_revision == revision for d in self.telemetry.deployments):
                raise ConflictError("Rollback target is not a known previous revision")
            if not any(m.revision == revision and m.error_rate < .01 and m.latency_ms < 200 for m in self.telemetry.metrics):
                raise ConflictError("Rollback target lacks a healthy baseline")
        else:
            revision = self.telemetry.service.revision
        if self.demo_url:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{self.demo_url}/control", json={"failure_mode": "none", "revision": revision}, headers={"Authorization": f"Bearer {self.operator_token}"} if self.operator_token else {})
                response.raise_for_status()
        self.telemetry.service.revision = revision
        self.telemetry.service.healthy = True
        for _ in range(5):
            sample = self.telemetry.healthy_sample()
            self.telemetry.append(sample, LogEntry(timestamp=sample.timestamp, revision=revision, message="Recovery verification: request succeeded"))
        return {"capability": action.capability, "revision": revision, "simulated": True, "samples": 5}
