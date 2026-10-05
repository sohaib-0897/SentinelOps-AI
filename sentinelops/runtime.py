import asyncio
from typing import Any

import httpx

from sentinelops.config import Settings
from sentinelops.detection import detect_incident
from sentinelops.domain.lifecycle import ConflictError, transition
from sentinelops.domain.models import AuditEvent, IncidentEvent, State
from sentinelops.persistence import SQLiteIncidentRepository
from sentinelops.providers.events import LocalEventBus
from sentinelops.providers.factory import build_providers
from sentinelops.providers.local import LocalTelemetryProvider
from sentinelops.simulation import SimulationEngine
from sentinelops.tools.operations import AgentTools
from sentinelops.workflows.investigation import IncidentWorkflow


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cloud_sql: Any = None
        if settings.cloud_sql_instance:
            from sentinelops.providers.gcp.cloud_sql import CloudSQLConnectionFactory
            self.cloud_sql = CloudSQLConnectionFactory(settings.cloud_sql_instance,settings.cloud_sql_user,settings.cloud_sql_database)
            self.repository = SQLiteIncidentRepository("postgresql+asyncpg://",self.cloud_sql.connect)
        else:
            self.repository = SQLiteIncidentRepository(settings.database_url)
        self.telemetry = LocalTelemetryProvider()
        self.bus = LocalEventBus(settings.event_buffer_size)
        self.simulation = SimulationEngine(self.telemetry)
        providers = build_providers(settings,self.telemetry,self.bus)
        self.workflow = IncidentWorkflow(self.repository, providers.events, AgentTools(providers.logs,providers.metrics,providers.deployments,providers.vectors), providers.llm,providers.remediation, delay=.5 if settings.app_env != "test" else 0)
        self.jobs: set[asyncio.Task[None]] = set()
        self.demo_task: asyncio.Task[None] | None = None
        self.control_lock = asyncio.Lock()
        self.last_error: str | None = None
        self.dispatcher_task: asyncio.Task[None] | None = None
        self.outbox_error: str | None = None

    async def initialize(self) -> None:
        await self.repository.initialize()
        snapshot = await self.repository.get_runtime("telemetry")
        if snapshot:
            self.telemetry.restore(snapshot)
        elif self.settings.demo_mode:
            for _ in range(8):
                self.telemetry.append(self.telemetry.healthy_sample())
        for incident in await self.repository.list_incidents(limit=1000):
            if incident.state in {State.TRIAGING, State.INVESTIGATING, State.REMEDIATING, State.VERIFYING}:
                transition(incident, State.FAILED)
                incident.timeline.append(IncidentEvent(kind="failure", message="Process restarted during workflow; operator review required before retry"))
                await self.repository.save(incident, [AuditEvent(incident_id=incident.id, actor="system", operation="interrupted_workflow")])
        self.dispatcher_task = asyncio.create_task(self.dispatch_events())

    async def close(self) -> None:
        tasks = [*self.jobs, *([self.demo_task] if self.demo_task else []), *([self.dispatcher_task] if self.dispatcher_task else [])]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.repository.close()
        if self.cloud_sql:
            await self.cloud_sql.close()

    def launch_investigation(self, incident_id: str) -> None:
        async def run() -> None:
            try:
                await self.workflow.investigate(incident_id)
            except (ConflictError, KeyError):
                return
            except Exception:
                self.last_error = "Investigation failed safely; inspect incident audit"
        task = asyncio.create_task(run())
        self.jobs.add(task)
        task.add_done_callback(self.jobs.discard)

    async def start_demo(self, name: str, restart: bool = False) -> dict[str, Any]:
        async with self.control_lock:
            active = [i for i in await self.repository.list_incidents(limit=1000) if i.state not in {State.RESOLVED, State.CLOSED, State.FAILED}]
            if active and not restart:
                raise ConflictError("An incident is active; use Restart to preserve it as an interrupted run")
            if any(i.state in {State.REMEDIATING, State.VERIFYING} for i in active):
                raise ConflictError("Wait for the current remediation to finish")
            for job in tuple(self.jobs):
                job.cancel()
            await asyncio.gather(*self.jobs, return_exceptions=True)
            for previous in active:
                incident = await self.workflow.require(previous.id)
                if incident.state not in {State.FAILED, State.RESOLVED, State.CLOSED}:
                    transition(incident, State.FAILED)
                    incident.timeline.append(IncidentEvent(kind="demo", message="Demo restarted; previous investigation retained"))
                    await self.workflow.persist(incident, "DemoRestarted")
            if self.demo_task:
                self.demo_task.cancel()
            self.simulation.start(name)
            if self.settings.connect_demo_service:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(f"{self.settings.demo_service_url}/control", json={"failure_mode":"none", "revision":"api-v1"}, headers={"Authorization":f"Bearer {self.settings.operator_token}"} if self.settings.operator_token else {})
                    response.raise_for_status()
            await self.repository.set_runtime("telemetry", self.telemetry.snapshot())
            await self.bus.publish({"type":"DemoStarted", "data":{"scenario":name}})
            self.demo_task = asyncio.create_task(self.demo_loop())
            return self.demo_status()

    async def demo_loop(self) -> None:
        try:
            while self.simulation.scenario:
                await asyncio.sleep(1.5 / self.simulation.speed)
                async with self.control_lock:
                    if self.simulation.paused:
                        continue
                    event = self.simulation.tick()
                    if self.settings.connect_demo_service and self.simulation.step == 2:
                        async with httpx.AsyncClient(timeout=10) as client:
                            response = await client.post(f"{self.settings.demo_service_url}/control", json={"failure_mode":"db_pool_exhaustion" if self.simulation.scenario.name == "bad-deployment" else {"dependency-timeout":"dependency_timeout", "http-500-spike":"http_500", "memory-pressure":"memory_pressure"}.get(self.simulation.scenario.name, "latency"), "revision":self.telemetry.service.revision}, headers={"Authorization":f"Bearer {self.settings.operator_token}"} if self.settings.operator_token else {})
                            response.raise_for_status()
                    await self.repository.set_runtime("telemetry", self.telemetry.snapshot())
                    await self.bus.publish({"type":"metrics", "data":event})
                    active = await self.repository.list_incidents(limit=1000)
                    incident = detect_incident(self.telemetry.metrics, active)
                    if incident:
                        await self.workflow.persist(incident, "IncidentDetected")
                        self.launch_investigation(incident.id)
                        self.simulation.paused = True
        except asyncio.CancelledError:
            raise
        except Exception:
            self.last_error = "Demo stopped safely; check service connectivity"
            await self.bus.publish({"type":"DemoError", "data":{"message":self.last_error}})

    def demo_status(self) -> dict[str, Any]:
        return {"scenario":self.simulation.scenario.name if self.simulation.scenario else None, "step":self.simulation.step, "paused":self.simulation.paused, "speed":self.simulation.speed, "error":self.last_error}

    async def dispatch_events(self) -> None:
        while True:
            await asyncio.sleep(3)
            for event in await self.repository.pending_events():
                try:
                    await self.workflow.bus.publish(event)
                    await self.repository.mark_delivered(str(event["id"]))
                    self.outbox_error = None
                except Exception:
                    self.outbox_error = "Event delivery pending; durable outbox will retry"
                    break
