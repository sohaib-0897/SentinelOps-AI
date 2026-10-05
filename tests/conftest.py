import pytest

from sentinelops.agents.common import AgentContext
from sentinelops.domain.models import Incident
from sentinelops.providers.local import DeterministicLLMProvider
from sentinelops.providers.vectors import LocalVectorProvider
from sentinelops.simulation import materialize
from sentinelops.tools.operations import AgentTools


@pytest.fixture
def agent_context() -> AgentContext:
    provider = materialize("bad-deployment")
    tools = AgentTools(provider, provider, provider, LocalVectorProvider())
    return AgentContext(Incident(title="Bad deployment"), tools, DeterministicLLMProvider())
