from sentinelops.agents.common import AgentContext
from sentinelops.agents.investigator import InvestigatorAgent
from sentinelops.agents.remediation import RemediationAgent
from sentinelops.agents.root_cause import RootCauseAgent
from sentinelops.agents.verification import VerificationAgent
from sentinelops.domain.models import IncidentEvent
from sentinelops.providers.remediation import LocalRemediationProvider


async def test_verification_requires_new_healthy_samples(agent_context: AgentContext) -> None:
    await InvestigatorAgent().run(agent_context)
    await RootCauseAgent().run(agent_context)
    await RemediationAgent().run(agent_context)
    telemetry = agent_context.tools.metrics
    boundary = telemetry.metrics[-1].timestamp.isoformat()
    agent_context.incident.timeline.append(IncidentEvent(kind="RemediationExecuted", message="test", data={"after_timestamp":boundary}))
    await VerificationAgent(attempts=1).run(agent_context)
    assert not agent_context.incident.verification.recovered
    await LocalRemediationProvider(telemetry).execute(agent_context.incident.remediation.actions[0])
    await VerificationAgent(attempts=1).run(agent_context)
    assert agent_context.incident.verification.recovered
    assert agent_context.incident.verification.samples == 5
    telemetry.metrics[-1].error_rate = .2
    await VerificationAgent(attempts=1).run(agent_context)
    assert agent_context.incident.verification.regression_detected
