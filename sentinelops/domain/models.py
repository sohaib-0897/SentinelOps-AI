from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def now() -> datetime:
    return datetime.now(UTC)


def identifier() -> str:
    return str(uuid4())


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class State(StrEnum):
    DETECTED = "DETECTED"
    TRIAGING = "TRIAGING"
    INVESTIGATING = "INVESTIGATING"
    DIAGNOSED = "DIAGNOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    CLOSED = "CLOSED"


class Risk(StrEnum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    PRIVILEGED = "PRIVILEGED"


class Service(Model):
    id: str = "orders-api"
    name: str = "Orders API"
    region: str = "local"
    revision: str = "api-v1"
    healthy: bool = True


class Deployment(Model):
    id: str = Field(default_factory=identifier)
    service_id: str
    revision: str
    previous_revision: str
    timestamp: datetime = Field(default_factory=now)
    changes: dict[str, str] = Field(default_factory=dict)
    healthy: bool = True


class MetricPoint(Model):
    timestamp: datetime = Field(default_factory=now)
    service_id: str = "orders-api"
    error_rate: float = Field(ge=0, le=1)
    latency_ms: float = Field(ge=0, le=120000)
    cpu: float = Field(ge=0, le=1)
    memory: float = Field(ge=0, le=1)
    db_connections: float = Field(ge=0, le=1)
    requests: int = Field(ge=0, le=10000000)
    revision: str = "api-v1"


class LogEntry(Model):
    id: str = Field(default_factory=identifier)
    timestamp: datetime = Field(default_factory=now)
    service_id: str = "orders-api"
    revision: str = "api-v1"
    severity: Literal["INFO", "WARNING", "ERROR"] = "INFO"
    message: str = Field(max_length=4000)
    labels: dict[str, str] = Field(default_factory=dict)


class Evidence(Model):
    id: str = Field(default_factory=identifier)
    source: Literal["logs", "metrics", "deployments", "history", "configuration", "health"]
    summary: str = Field(min_length=1, max_length=4000)
    timestamp: datetime = Field(default_factory=now)
    data: dict[str, Any] = Field(default_factory=dict)


class Hypothesis(Model):
    id: str = Field(default_factory=identifier)
    cause: str
    description: str
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=now)


class RootCauseAnalysis(Model):
    hypothesis_id: str
    cause: str
    confidence: float = Field(ge=0, le=1)
    explanation: str
    evidence_ids: list[str] = Field(min_length=1)


class RemediationAction(Model):
    id: str = Field(default_factory=identifier)
    capability: Literal["restart_demo_service", "rollback_demo_revision", "change_demo_traffic_split", "simulate_scale_up"]
    service_id: str
    risk: Risk = Risk.PRIVILEGED
    parameters: dict[str, str] = Field(default_factory=dict)


class RemediationPlan(Model):
    id: str = Field(default_factory=identifier)
    summary: str
    actions: list[RemediationAction] = Field(min_length=1, max_length=4)
    created_at: datetime = Field(default_factory=now)
    expires_at: datetime
    status: Literal["proposed", "approved", "executing", "executed", "failed"] = "proposed"


class Approval(Model):
    id: str = Field(default_factory=identifier)
    incident_id: str
    plan_id: str
    plan_digest: str
    action_ids: list[str]
    actor: str = Field(min_length=1, max_length=120)
    risk: Risk = Risk.PRIVILEGED
    timestamp: datetime = Field(default_factory=now)


class IncidentEvent(Model):
    id: str = Field(default_factory=identifier)
    timestamp: datetime = Field(default_factory=now)
    kind: str
    actor: str = "system"
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class HistoricalIncident(Model):
    id: str
    title: str
    signature: str
    cause: str
    remediation: str
    outcome: str = "resolved"
    similarity: float = Field(default=0, ge=0, le=1)


class Verification(Model):
    recovered: bool
    samples: int = Field(ge=0)
    before_error_rate: float
    after_error_rate: float
    before_latency_ms: float
    after_latency_ms: float
    regression_detected: bool = False
    checks: dict[str, bool]
    timestamp: datetime = Field(default_factory=now)


class Postmortem(Model):
    summary: str
    impact: str
    timeline: list[IncidentEvent]
    root_cause: str
    detection: str
    response: str
    remediation: str
    what_worked: list[str]
    what_failed: list[str]
    prevention: list[str]
    follow_up_actions: list[str]
    generated_at: datetime = Field(default_factory=now)


class AuditEvent(Model):
    id: str = Field(default_factory=identifier)
    incident_id: str | None = None
    actor: str
    operation: str
    timestamp: datetime = Field(default_factory=now)
    details: dict[str, Any] = Field(default_factory=dict)


class Incident(Model):
    id: str = Field(default_factory=identifier)
    title: str
    service_id: str = "orders-api"
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    state: State = State.DETECTED
    started_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
    resolved_at: datetime | None = None
    version: int = Field(default=0, ge=0)
    symptoms: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    root_cause: RootCauseAnalysis | None = None
    historical_matches: list[HistoricalIncident] = Field(default_factory=list)
    remediation: RemediationPlan | None = None
    approvals: list[Approval] = Field(default_factory=list)
    verification: Verification | None = None
    postmortem: Postmortem | None = None
    timeline: list[IncidentEvent] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)

    @field_validator("started_at", "updated_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Timestamp must include a timezone")
        return value
