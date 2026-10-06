from sentinelops.agents.common import AgentContext
from sentinelops.agents.investigator import InvestigatorAgent


async def test_investigator_preserves_sources_and_timestamps(agent_context: AgentContext) -> None:
    await InvestigatorAgent().run(agent_context)
    incident = agent_context.incident
    assert {e.source for e in incident.evidence} >= {"logs", "metrics", "deployments", "configuration"}
    metrics = next(e for e in incident.evidence if "onset" in e.data)
    deployment = next(e for e in incident.evidence if e.source == "deployments")
    assert (metrics.timestamp - deployment.timestamp).total_seconds() == 37
