from sentinelops.agents.common import AgentContext
from sentinelops.detection import threshold_exceeded
from sentinelops.domain.models import Evidence, IncidentEvent
from sentinelops.tools.operations import ServiceQuery


class InvestigatorAgent:
    async def run(self, context: AgentContext) -> None:
        query = ServiceQuery(service_id=context.incident.service_id, limit=120)
        context.activity("INVESTIGATOR", "Querying application logs and metric history")
        logs = await context.tools.search_logs(query)
        metrics = await context.tools.get_metric_series(query)
        deployments = await context.tools.get_recent_deployments(query)
        changes = await context.tools.compare_revisions(query)
        evidence = context.incident.evidence
        if logs:
            evidence.append(Evidence(source="logs", summary=f"{len(logs)} log entries collected; {sum(entry.severity == 'ERROR' for entry in logs)} errors", timestamp=logs[0].timestamp, data={"entries": [entry.model_dump(mode="json") for entry in logs]}))
            context.activity("INVESTIGATOR", f"{sum(entry.severity == 'ERROR' for entry in logs)} application errors identified")
        if metrics:
            point = metrics[-1]
            onset = next((m.timestamp for m in metrics if threshold_exceeded(m)), point.timestamp)
            evidence.append(Evidence(source="metrics", summary=f"Error rate {point.error_rate:.1%}, p95 latency {point.latency_ms:.0f}ms, DB connections {point.db_connections:.0%}", timestamp=onset, data={"series": [m.model_dump(mode="json") for m in metrics], "latest": point.model_dump(mode="json"), "onset": onset.isoformat()}))
            evidence.append(Evidence(source="metrics", summary=f"CPU utilization {'remained normal' if point.cpu < .5 else 'elevated'} at {point.cpu:.0%}", data={"cpu": point.cpu}))
        for deployment in deployments[-3:]:
            evidence.append(Evidence(source="deployments", summary=f"Revision {deployment.revision} deployed; previous revision {deployment.previous_revision}", timestamp=deployment.timestamp, data=deployment.model_dump(mode="json")))
            context.incident.timeline.append(IncidentEvent(timestamp=deployment.timestamp, kind="DeploymentCreated", message=f"Revision {deployment.revision} deployed", data={"revision": deployment.revision}))
        if changes:
            evidence.append(Evidence(source="configuration", summary="Revision configuration changed", data={"changes": changes}))
        context.activity("INVESTIGATOR", f"Collected {len(evidence)} structured evidence records from logs, metrics and deployments")
