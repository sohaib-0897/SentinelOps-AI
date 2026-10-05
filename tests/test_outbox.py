from unittest.mock import AsyncMock

from sentinelops.domain.models import Incident
from sentinelops.persistence import SQLiteIncidentRepository
from sentinelops.providers.events import LocalEventBus
from sentinelops.providers.local import DeterministicLLMProvider, LocalTelemetryProvider
from sentinelops.providers.remediation import LocalRemediationProvider
from sentinelops.providers.vectors import LocalVectorProvider
from sentinelops.tools.operations import AgentTools
from sentinelops.workflows.investigation import IncidentWorkflow


async def test_publication_failure_retains_committed_event_for_retry() -> None:
    repo = SQLiteIncidentRepository("sqlite+aiosqlite:///:memory:")
    await repo.initialize()
    telemetry = LocalTelemetryProvider()
    bus = LocalEventBus()
    bus.publish = AsyncMock(side_effect=RuntimeError("external service unavailable"))
    workflow = IncidentWorkflow(repo,bus,AgentTools(telemetry,telemetry,telemetry,LocalVectorProvider()),DeterministicLLMProvider(),LocalRemediationProvider(telemetry))
    incident = Incident(title="test")
    await workflow.persist(incident,"IncidentDetected")
    assert (await repo.get(incident.id)).version == 1
    pending = await repo.pending_events()
    assert len(pending) == 1 and pending[0]["type"] == "IncidentDetected"
    await repo.mark_delivered(pending[0]["id"])
    assert not await repo.pending_events()
    await repo.close()
