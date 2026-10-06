from sentinelops.agents.common import AgentContext
from sentinelops.agents.historical import HistoricalAgent
from sentinelops.agents.investigator import InvestigatorAgent


async def test_historical_agent_links_matches_to_evidence(agent_context: AgentContext) -> None:
    await InvestigatorAgent().run(agent_context)
    await HistoricalAgent().run(agent_context)
    assert "INC-007" in {match.id for match in agent_context.incident.historical_matches}
    assert any(e.source == "history" for e in agent_context.incident.evidence)
