import asyncio

import pytest

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import Incident, State
from sentinelops.persistence import SQLiteIncidentRepository
from sentinelops.providers.events import LocalEventBus
from sentinelops.providers.local import DeterministicLLMProvider
from sentinelops.providers.remediation import LocalRemediationProvider
from sentinelops.providers.vectors import LocalVectorProvider
from sentinelops.simulation import materialize
from sentinelops.tools.operations import AgentTools
from sentinelops.workflows.investigation import IncidentWorkflow


async def test_complete_approved_workflow_and_concurrent_replay() -> None:
    repository = SQLiteIncidentRepository("sqlite+aiosqlite:///:memory:")
    await repository.initialize()
    provider = materialize("bad-deployment")
    workflow = IncidentWorkflow(repository, LocalEventBus(), AgentTools(provider, provider, provider, LocalVectorProvider()), DeterministicLLMProvider(), LocalRemediationProvider(provider))
    incident = Incident(title="Bad deployment")
    await repository.save(incident)
    investigated = await workflow.investigate(incident.id)
    assert investigated.state == State.AWAITING_APPROVAL
    assert len(investigated.hypotheses) == 3
    assert investigated.root_cause.confidence == .94
    with pytest.raises(ConflictError):
        await workflow.execute(incident.id, "sre")
    await workflow.approve(incident.id, investigated.remediation.id, "sre")
    results = await asyncio.gather(workflow.execute(incident.id, "sre"), workflow.execute(incident.id, "sre"), return_exceptions=True)
    assert sum(isinstance(r, ConflictError) for r in results) == 1
    resolved = await repository.get(incident.id)
    assert resolved.state == State.RESOLVED
    assert resolved.postmortem and resolved.verification.recovered
    assert len(await repository.audit(incident.id)) == 4
    await repository.close()
