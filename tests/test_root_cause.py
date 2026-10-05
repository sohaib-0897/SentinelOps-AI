import pytest

from sentinelops.agents.common import AgentContext
from sentinelops.agents.investigator import InvestigatorAgent
from sentinelops.agents.root_cause import RootCauseAgent
from sentinelops.domain.models import Incident
from sentinelops.providers.local import DeterministicLLMProvider
from sentinelops.providers.vectors import LocalVectorProvider
from sentinelops.simulation import materialize, scenarios
from sentinelops.tools.operations import AgentTools


@pytest.mark.parametrize("name", [n for n, s in scenarios().items() if s.expected_root_cause])
async def test_causes_require_observed_evidence(name: str) -> None:
    provider = materialize(name)
    context = AgentContext(Incident(title="test"), AgentTools(provider, provider, provider, LocalVectorProvider()), DeterministicLLMProvider())
    await InvestigatorAgent().run(context)
    await RootCauseAgent().run(context)
    if name == "insufficient-evidence":
        assert context.incident.root_cause is None
    else:
        root = context.incident.root_cause
        assert root and root.cause == scenarios()[name].expected_root_cause
        assert len(root.evidence_ids) >= 2
        assert set(root.evidence_ids) <= {e.id for e in context.incident.evidence}


async def test_no_evidence_no_root_cause(agent_context: AgentContext) -> None:
    await RootCauseAgent().run(agent_context)
    assert agent_context.incident.root_cause is None
