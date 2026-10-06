from sentinelops.agents.common import AgentContext
from sentinelops.domain.models import Evidence
from sentinelops.tools.operations import ServiceQuery


class HistoricalAgent:
    async def run(self, context: AgentContext) -> None:
        entries = [str(entry["message"]) for e in context.incident.evidence if e.source == "logs" for entry in e.data.get("entries", [])]
        deployment_context = ["deployment " + e.summary for e in context.incident.evidence if e.source == "deployments"]
        query = " ".join(list(dict.fromkeys(entries)) + deployment_context + context.incident.symptoms)[:512]
        matches = await context.tools.search_historical_incidents(ServiceQuery(service_id=context.incident.service_id, query=query, limit=3))
        context.incident.historical_matches = matches
        for match in matches:
            context.incident.evidence.append(Evidence(source="history", summary=f"Historical incident {match.id}: {match.title}", data=match.model_dump(mode="json")))
        context.activity("HISTORICAL", f"Retrieved {len(matches)} similar historical incidents" + (f"; closest match {matches[0].id}" if matches else ""))
