from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast

from alembic import command
from alembic.config import Config
from sqlalchemy import JSON, Boolean, Integer, String, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import AuditEvent, Incident, now


class Base(DeclarativeBase):
    pass


class IncidentRow(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    service_id: Mapped[str] = mapped_column(String(128), index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class AuditRow(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str | None] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class RuntimeRow(Base):
    __tablename__ = "runtime_state"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class OutboxRow(Base):
    __tablename__ = "event_outbox"
    id: Mapped[str] = mapped_column(String(64),primary_key=True)
    delivered: Mapped[bool] = mapped_column(Boolean,default=False,index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class SQLiteIncidentRepository:
    def __init__(self, database_url: str, async_creator: Callable[[], Awaitable[Any]] | None = None) -> None:
        self.database_url = database_url
        options: dict[str, Any] = {"connect_args":{"timeout":30}} if "sqlite" in database_url else {"pool_pre_ping":True}
        if async_creator:
            options["async_creator"] = async_creator
        self.engine = create_async_engine(database_url, **options)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def initialize(self) -> None:
        if ":memory:" in self.database_url:
            async with self.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        else:
            config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            config.set_main_option("sqlalchemy.url", self.database_url)
            async with self.engine.begin() as connection:
                def migrate(sync_connection: Any) -> None:
                    config.attributes["connection"] = sync_connection
                    command.upgrade(config,"head")
                await connection.run_sync(migrate)

    async def close(self) -> None:
        await self.engine.dispose()

    async def get(self, incident_id: str) -> Incident | None:
        async with self.sessions() as session:
            row = await session.get(IncidentRow, incident_id)
            return Incident.model_validate(row.payload) if row else None

    async def list_incidents(self, limit: int = 100, offset: int = 0) -> list[Incident]:
        async with self.sessions() as session:
            rows = (await session.scalars(select(IncidentRow).order_by(IncidentRow.id).limit(limit).offset(offset))).all()
            return sorted((Incident.model_validate(row.payload) for row in rows), key=lambda i: i.started_at, reverse=True)

    async def save(self, incident: Incident, audit: list[AuditEvent] | None = None, events: list[dict[str, Any]] | None = None) -> None:
        previous = incident.version
        candidate = incident.model_copy(deep=True)
        candidate.version = previous + 1
        candidate.updated_at = now()
        payload = candidate.model_dump(mode="json")
        async with self.sessions.begin() as session:
            if previous == 0:
                if await session.get(IncidentRow, incident.id):
                    raise ConflictError("Incident already exists")
                session.add(IncidentRow(id=incident.id, service_id=incident.service_id, state=incident.state, version=1, payload=payload))
            else:
                result = await session.execute(update(IncidentRow).where(IncidentRow.id == incident.id, IncidentRow.version == previous).values(state=incident.state, version=candidate.version, payload=payload))
                if cast(CursorResult[Any], result).rowcount != 1:
                    raise ConflictError("Incident changed; reload before retrying")
            for event in audit or []:
                session.add(AuditRow(id=event.id, incident_id=event.incident_id, payload=event.model_dump(mode="json")))
            for envelope in events or []:
                session.add(OutboxRow(id=envelope["id"],delivered=False,payload=envelope))
        incident.version = candidate.version
        incident.updated_at = candidate.updated_at

    async def audit(self, incident_id: str | None = None) -> list[AuditEvent]:
        async with self.sessions() as session:
            query = select(AuditRow)
            if incident_id:
                query = query.where(AuditRow.incident_id == incident_id)
            rows = (await session.scalars(query)).all()
            return sorted((AuditEvent.model_validate(row.payload) for row in rows), key=lambda a: a.timestamp)

    async def set_runtime(self, key: str, payload: dict[str, Any]) -> None:
        async with self.sessions.begin() as session:
            await session.merge(RuntimeRow(key=key, payload=payload))

    async def get_runtime(self, key: str) -> dict[str, Any] | None:
        async with self.sessions() as session:
            row = await session.get(RuntimeRow, key)
            return row.payload if row else None

    async def pending_events(self, limit: int = 100) -> list[dict[str, Any]]:
        async with self.sessions() as session:
            rows = (await session.scalars(select(OutboxRow).where(OutboxRow.delivered.is_(False)).limit(limit))).all()
            return [row.payload for row in rows]

    async def mark_delivered(self, event_id: str) -> None:
        async with self.sessions.begin() as session:
            await session.execute(update(OutboxRow).where(OutboxRow.id == event_id).values(delivered=True))
