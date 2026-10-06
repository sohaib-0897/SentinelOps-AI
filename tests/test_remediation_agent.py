from sentinelops.agents.common import AgentContext
from sentinelops.agents.investigator import InvestigatorAgent
from sentinelops.agents.remediation import RemediationAgent
from sentinelops.agents.root_cause import RootCauseAgent
from sentinelops.domain.models import Risk


async def test_rollback_is_proposed_never_executed(agent_context: AgentContext) -> None:
    await InvestigatorAgent().run(agent_context)
    await RootCauseAgent().run(agent_context)
    await RemediationAgent().run(agent_context)
    plan = agent_context.incident.remediation
    assert plan and plan.status == "proposed"
    assert plan.actions[0].capability == "rollback_demo_revision"
    assert plan.actions[0].parameters["revision"] == "api-v1"
    assert plan.actions[0].risk == Risk.PRIVILEGED


async def test_no_supported_cause_no_action(agent_context: AgentContext) -> None:
    await RemediationAgent().run(agent_context)
    assert agent_context.incident.remediation is None
