import pytest
from pydantic import ValidationError

from sentinelops.providers.vectors import LocalVectorProvider
from sentinelops.simulation import materialize
from sentinelops.tools.operations import AgentTools, ServiceQuery


async def test_typed_tools_and_bounded_runbook_paths() -> None:
    provider = materialize("bad-deployment")
    tools = AgentTools(provider, provider, provider, LocalVectorProvider())
    query = ServiceQuery()
    assert await tools.get_error_rate(query) == .18
    assert await tools.get_latency(query) == 1680
    assert (await tools.get_revision_details(query, "api-v2")).previous_revision == "api-v1"
    assert "Investigate" in await tools.retrieve_runbook("../../.env")
    assert "execute_shell" not in tools.READ_CAPABILITIES


def test_queries_validate_inputs() -> None:
    with pytest.raises(ValidationError):
        ServiceQuery(service_id="../../etc", limit=10000)
