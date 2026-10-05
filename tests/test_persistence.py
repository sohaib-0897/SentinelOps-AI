from pathlib import Path

import pytest

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import AuditEvent, Incident
from sentinelops.persistence import SQLiteIncidentRepository


async def test_round_trip_and_optimistic_lock(tmp_path: Path) -> None:
    repository = SQLiteIncidentRepository(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await repository.initialize()
    incident = Incident(title="Database issue")
    await repository.save(incident)
    first = await repository.get(incident.id)
    stale = await repository.get(incident.id)
    assert first and stale
    first.title = "Updated"
    await repository.save(first, [AuditEvent(actor="operator", operation="test", incident_id=first.id)])
    with pytest.raises(ConflictError):
        await repository.save(stale, [AuditEvent(actor="operator", operation="must-not-persist")])
    assert len(await repository.audit()) == 1
    assert (await repository.list_incidents())[0].title == "Updated"
    await repository.close()
    reopened = SQLiteIncidentRepository(repository.database_url)
    await reopened.initialize()
    assert (await reopened.get(incident.id)).version == 2
    await reopened.close()


async def test_runtime_state_survives(tmp_path: Path) -> None:
    repository = SQLiteIncidentRepository(f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}")
    await repository.initialize()
    await repository.set_runtime("demo", {"revision": "v2"})
    assert await repository.get_runtime("demo") == {"revision": "v2"}
    assert await repository.get("missing") is None
    await repository.close()
