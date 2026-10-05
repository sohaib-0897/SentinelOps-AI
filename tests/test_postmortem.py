import pytest

from sentinelops.agents.common import AgentContext
from sentinelops.agents.postmortem import PostmortemAgent


async def test_postmortem_cannot_fabricate_recovery(agent_context: AgentContext) -> None:
    with pytest.raises(ValueError):
        await PostmortemAgent().run(agent_context)
