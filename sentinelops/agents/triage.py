from sentinelops.agents.common import AgentContext
from sentinelops.tools.operations import ServiceQuery


class TriageAgent:
    async def run(self, context: AgentContext) -> None:
        query = ServiceQuery(service_id=context.incident.service_id)
        error_rate = await context.tools.get_error_rate(query)
        latency = await context.tools.get_latency(query)
        health = await context.tools.get_service_health(query)
        context.incident.severity = "CRITICAL" if error_rate >= .3 else "HIGH" if error_rate >= .05 or latency >= 800 else "MEDIUM"
        context.incident.symptoms = [f"HTTP error rate {error_rate:.1%}", f"p95 latency {latency:.0f}ms", f"Revision {health.revision}"]
        context.activity("TRIAGE", f"Incident classified {context.incident.severity} severity; affected service {health.name}")
