from sentinelops.agents.common import AgentContext
from sentinelops.agents.triage import TriageAgent


async def test_triage_classifies_observed_health(agent_context: AgentContext) -> None:
    await TriageAgent().run(agent_context)
    assert agent_context.incident.severity == "HIGH"
    assert "get_error_rate" in agent_context.tools.calls
    assert "18.0%" in agent_context.incident.symptoms[0]
