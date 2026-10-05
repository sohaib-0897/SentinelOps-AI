import asyncio
from datetime import datetime
from statistics import mean

from sentinelops.agents.common import AgentContext
from sentinelops.domain.models import MetricPoint, Verification
from sentinelops.tools.operations import ServiceQuery


class VerificationAgent:
    def __init__(self, attempts: int = 6, interval: float = 1) -> None:
        self.attempts = attempts
        self.interval = interval

    async def run(self, context: AgentContext) -> None:
        incident = context.incident
        baseline = next((MetricPoint.model_validate(e.data["latest"]) for e in incident.evidence if "latest" in e.data), None)
        boundary_event = next((e for e in reversed(incident.timeline) if e.kind == "RemediationExecuted"), None)
        boundary = datetime.fromisoformat(boundary_event.data["after_timestamp"]) if boundary_event else None
        query = ServiceQuery(service_id=incident.service_id, limit=120)
        points: list[MetricPoint] = []
        for attempt in range(self.attempts):
            series = await context.tools.get_metric_series(query)
            points = [p for p in series if boundary and p.timestamp > boundary][-5:]
            if len(points) >= 5:
                break
            if attempt + 1 < self.attempts:
                await asyncio.sleep(self.interval)
        health = await context.tools.get_service_health(query)
        logs = await context.tools.search_logs(query)
        after_logs = [entry for entry in logs if boundary and entry.timestamp > boundary]
        expected = incident.remediation.actions[0].parameters.get("revision") if incident.remediation else None
        checks = {
            "five_samples": len(points) >= 5,
            "error_rate": bool(points) and all(p.error_rate <= .01 for p in points),
            "latency": bool(points) and all(p.latency_ms <= 200 for p in points),
            "resources": bool(points) and all(p.cpu < .8 and p.memory < .8 and p.db_connections < .8 for p in points),
            "logs": bool(after_logs) and not any(entry.severity == "ERROR" for entry in after_logs),
            "service_health": health.healthy,
            "revision": expected is None or health.revision == expected,
        }
        incident.verification = Verification(recovered=all(checks.values()), samples=len(points), before_error_rate=baseline.error_rate if baseline else 0, after_error_rate=mean(p.error_rate for p in points) if points else 1, before_latency_ms=baseline.latency_ms if baseline else 0, after_latency_ms=mean(p.latency_ms for p in points) if points else 120000, regression_detected=bool(points) and not all(checks.values()), checks=checks)
        context.activity("VERIFICATION", f"Recovery {'confirmed' if incident.verification.recovered else 'not confirmed'} across {len(points)} post-remediation samples")
