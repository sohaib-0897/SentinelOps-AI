from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import AuditEvent, Incident, now
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


async def test_pagination_orders_by_time_before_selecting_rows(tmp_path: Path) -> None:
    repository = SQLiteIncidentRepository(f"sqlite+aiosqlite:///{tmp_path / 'ordered.db'}")
    await repository.initialize()
    start = now()
    for index, key in enumerate(["z-old", "m-middle", "a-new"]):
        await repository.save(Incident(id=key, title=key, started_at=start+timedelta(seconds=index)))
    assert [row.id for row in await repository.list_incidents(limit=1)] == ["a-new"]
    assert [row.id for row in await repository.list_incidents(limit=1, offset=1)] == ["m-middle"]
    assert [row.id for row in await repository.list_incidents(limit=1, offset=2)] == ["z-old"]
    await repository.close()


async def test_order_migration_preserves_existing_incidents(tmp_path: Path) -> None:
    repository = SQLiteIncidentRepository(f"sqlite+aiosqlite:///{tmp_path / 'upgrade.db'}")
    incident = Incident(id="retained", title="Retained before migration")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", repository.database_url)
    async with repository.engine.begin() as connection:
        def old_schema(sync):
            config.attributes["connection"] = sync
            command.upgrade(config, "0002")
        await connection.run_sync(old_schema)
        await connection.execute(text("INSERT INTO incidents (id,service_id,state,version,payload) VALUES (:id,:service,:state,1,:payload)"), {"id":incident.id,"service":incident.service_id,"state":incident.state,"payload":incident.model_dump_json()})
    await repository.initialize()
    rows = await repository.list_incidents()
    assert len(rows) == 1 and rows[0].title == incident.title
    assert rows[0].started_at == incident.started_at
    await repository.close()
