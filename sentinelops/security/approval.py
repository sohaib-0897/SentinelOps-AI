import hashlib
import json
import re

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import (
    Approval,
    Incident,
    RemediationAction,
    RemediationPlan,
    Risk,
    State,
    now,
)

CAPABILITIES = {
    "restart_demo_service": Risk.PRIVILEGED,
    "rollback_demo_revision": Risk.PRIVILEGED,
    "change_demo_traffic_split": Risk.PRIVILEGED,
    "simulate_scale_up": Risk.PRIVILEGED,
}


def plan_digest(plan: RemediationPlan) -> str:
    payload = plan.model_dump(mode="json", exclude={"status"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_action(action: RemediationAction, service_id: str) -> None:
    if action.capability not in CAPABILITIES or action.risk != CAPABILITIES[action.capability]:
        raise ConflictError("Capability risk does not match policy")
    if action.service_id != service_id:
        raise ConflictError("Action service does not match incident")
    parameters = action.parameters
    if action.capability in {"rollback_demo_revision", "change_demo_traffic_split"}:
        if set(parameters) != {"revision", "expected_revision"} or not all(re.fullmatch(r"[a-z][a-z0-9-]{0,62}", value) for value in parameters.values()):
            raise ConflictError("Revision action requires validated revision preconditions")
        if parameters["revision"] == parameters["expected_revision"]:
            raise ConflictError("Target must differ from current revision")
    elif action.capability == "simulate_scale_up":
        if set(parameters) != {"instances"} or parameters["instances"] not in {"2", "3", "4"}:
            raise ConflictError("Scale simulation is bounded to 2–4 instances")
    elif parameters:
        raise ConflictError("Restart does not accept arbitrary parameters")


def approve(incident: Incident, plan_id: str, actor: str) -> Approval:
    plan = incident.remediation
    if incident.state != State.AWAITING_APPROVAL or not plan or plan.id != plan_id:
        raise ConflictError("Incident is not awaiting approval for this plan")
    if plan.expires_at <= now() or plan.status != "proposed":
        raise ConflictError("Plan expired or has already been approved")
    for action in plan.actions:
        validate_action(action, incident.service_id)
    approval = Approval(incident_id=incident.id, plan_id=plan.id, plan_digest=plan_digest(plan), action_ids=[a.id for a in plan.actions], actor=actor)
    incident.approvals.append(approval)
    plan.status = "approved"
    return approval


def authorize(incident: Incident) -> RemediationPlan:
    plan = incident.remediation
    if incident.state != State.AWAITING_APPROVAL or not plan or plan.status != "approved" or plan.expires_at <= now():
        raise ConflictError("A current, approved plan is required")
    for action in plan.actions:
        validate_action(action, incident.service_id)
    if not any(a.plan_id == plan.id and a.incident_id == incident.id and a.plan_digest == plan_digest(plan) and a.action_ids == [action.id for action in plan.actions] for a in incident.approvals):
        raise ConflictError("Approval is missing or plan changed after approval")
    return plan
