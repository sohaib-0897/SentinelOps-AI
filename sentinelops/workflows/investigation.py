import asyncio
from typing import Any

from sentinelops.agents.common import Agent, AgentContext
from sentinelops.agents.historical import HistoricalAgent
from sentinelops.agents.investigator import InvestigatorAgent
from sentinelops.agents.postmortem import PostmortemAgent
from sentinelops.agents.remediation import RemediationAgent
from sentinelops.agents.root_cause import RootCauseAgent
from sentinelops.agents.triage import TriageAgent
from sentinelops.agents.verification import VerificationAgent
from sentinelops.domain.lifecycle import ConflictError, transition
from sentinelops.domain.models import AuditEvent, Incident, IncidentEvent, State, event_time
from sentinelops.providers.contracts import (
    EventBus,
    IncidentRepository,
    LLMProvider,
    RemediationProvider,
)
from sentinelops.providers.events import DomainEvent
from sentinelops.security.approval import approve, authorize
from sentinelops.tools.operations import AgentTools, ServiceQuery


class IncidentWorkflow:
    def __init__(self, repository: IncidentRepository, bus: EventBus, tools: AgentTools, llm: LLMProvider, executor: RemediationProvider, delay: float = 0) -> None:
        self.repository = repository
        self.bus = bus
        self.tools = tools
        self.llm = llm
        self.executor = executor
        self.delay = delay
        self.locks: dict[str, asyncio.Lock] = {}

    def lock(self, incident_id: str) -> asyncio.Lock:
        return self.locks.setdefault(incident_id, asyncio.Lock())

    async def require(self, incident_id: str) -> Incident:
        incident = await self.repository.get(incident_id)
        if not incident:
            raise KeyError("Incident not found")
        return incident

    async def persist(self, incident: Incident, kind: str, audit: list[AuditEvent] | None = None) -> None:
        event = DomainEvent(type=kind,incident_id=incident.id,data={"version":incident.version+1}).model_dump(mode="json")
        await self.repository.save(incident,audit,[event])
        try:
            await self.bus.publish(event)
            await self.repository.mark_delivered(str(event["id"]))
        except Exception:
            # Durable outbox retries delivery. Publication failure must not undo execution claims.
            return

    def context(self, incident: Incident) -> AgentContext:
        tools = AgentTools(self.tools.logs, self.tools.metrics, self.tools.deployments, self.tools.vectors)
        return AgentContext(incident, tools, self.llm)

    async def investigate(self, incident_id: str) -> Incident:
        async with self.lock(incident_id):
            incident = await self.require(incident_id)
            if incident.state not in {State.DETECTED, State.FAILED}:
                raise ConflictError("Investigation has already started")
            context = self.context(incident)
            if incident.state == State.DETECTED:
                transition(incident, State.TRIAGING)
                await self.persist(incident, "InvestigationStarted")
                await TriageAgent().run(context)
            else:
                incident.evidence = []
                incident.hypotheses = []
                incident.root_cause = None
                incident.remediation = None
                incident.approvals = []
            transition(incident, State.INVESTIGATING)
            await self.persist(incident, "InvestigationStarted")
            agents: list[tuple[Agent, str]] = [(InvestigatorAgent(), "EvidenceCollected"), (HistoricalAgent(), "HistoricalMatchesRetrieved"), (RootCauseAgent(), "HypothesisUpdated"), (RemediationAgent(), "RemediationProposed")]
            try:
                for agent, event in agents:
                    await agent.run(context)
                    incident.tool_calls = context.tools.calls.copy()
                    await self.persist(incident, event)
                    if self.delay:
                        await asyncio.sleep(self.delay)
                if not incident.root_cause or not incident.remediation:
                    transition(incident, State.FAILED)
                    context.activity("SYSTEM", "More evidence or an operator runbook is required; no remediation authorized")
                    await self.persist(incident, "InvestigationInconclusive")
                    return incident
                transition(incident, State.DIAGNOSED)
                await self.persist(incident, "RootCauseDetermined")
                transition(incident, State.AWAITING_APPROVAL)
                context.activity("SYSTEM", "Waiting for human approval")
                await self.persist(incident, "RemediationProposed")
                return incident
            except Exception as error:
                await self.fail(incident, error)
                raise

    async def approve(self, incident_id: str, plan_id: str, actor: str) -> Incident:
        async with self.lock(incident_id):
            incident = await self.require(incident_id)
            approval = approve(incident, plan_id, actor)
            incident.timeline.append(IncidentEvent(timestamp=event_time(incident),kind="RemediationApproved", actor=actor, message="Exact remediation plan approved", data={"plan_id":plan_id}))
            await self.persist(incident, "RemediationApproved", [AuditEvent(incident_id=incident_id, actor=actor, operation="remediation_approved", details=approval.model_dump(mode="json"))])
            return incident

    async def execute(self, incident_id: str, actor: str) -> Incident:
        async with self.lock(incident_id):
            incident = await self.require(incident_id)
            plan = authorize(incident)
            context = self.context(incident)
            metrics = await context.tools.get_metric_series(ServiceQuery(service_id=incident.service_id, limit=1))
            if not metrics:
                raise ConflictError("Current metrics required before remediation")
            boundary = metrics[-1].timestamp.isoformat()
            transition(incident, State.REMEDIATING, actor)
            plan.status = "executing"
            await self.persist(incident, "RemediationStarted", [AuditEvent(incident_id=incident_id, actor=actor, operation="execution_claimed", details={"plan_id":plan.id})])
            try:
                results: list[dict[str, Any]] = []
                for action in plan.actions:
                    results.append(await self.executor.execute(action))
                plan.status = "executed"
                incident.timeline.append(IncidentEvent(timestamp=event_time(incident),kind="RemediationExecuted", actor=actor, message=plan.summary, data={"after_timestamp":boundary, "results":results}))
                transition(incident, State.VERIFYING)
                await self.persist(incident, "RemediationExecuted", [AuditEvent(incident_id=incident_id, actor=actor, operation="remediation_executed", details={"plan_id":plan.id, "results":results})])
                await VerificationAgent().run(context)
                incident.tool_calls.extend(context.tools.calls)
                if not incident.verification or not incident.verification.recovered:
                    transition(incident, State.FAILED)
                    await self.persist(incident, "VerificationFailed")
                    return incident
                await self.persist(incident, "RecoveryDetected")
                transition(incident, State.RESOLVED)
                await PostmortemAgent().run(context)
                await self.persist(incident, "IncidentResolved", [AuditEvent(incident_id=incident_id, actor="system", operation="recovery_verified")])
                return incident
            except Exception as error:
                plan.status = "failed"
                await self.fail(incident, error)
                raise

    async def fail(self, incident: Incident, error: Exception) -> None:
        if incident.state not in {State.FAILED, State.RESOLVED, State.CLOSED}:
            transition(incident, State.FAILED)
        incident.timeline.append(IncidentEvent(timestamp=event_time(incident),kind="failure", message="Operation failed safely; inspect audit and retry investigation after review"))
        await self.persist(incident, "WorkflowFailed", [AuditEvent(incident_id=incident.id, actor="system", operation="workflow_failed", details={"error_type":type(error).__name__})])
