from datetime import timedelta

import pytest

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import Incident, RemediationAction, RemediationPlan, Risk, State, now
from sentinelops.security.approval import approve, authorize, validate_action


def planned() -> Incident:
    return Incident(title="test", state=State.AWAITING_APPROVAL, remediation=RemediationPlan(summary="Rollback", expires_at=now()+timedelta(minutes=10), actions=[RemediationAction(capability="rollback_demo_revision", service_id="orders-api", parameters={"revision":"api-v1", "expected_revision":"api-v2"})]))


def test_exact_plan_approval_and_tamper_rejection() -> None:
    incident = planned()
    with pytest.raises(ConflictError):
        authorize(incident)
    approval = approve(incident, incident.remediation.id, "sre")
    assert approval.actor == "sre"
    assert authorize(incident).status == "approved"
    incident.remediation.actions[0].parameters["revision"] = "api-v3"
    with pytest.raises(ConflictError):
        authorize(incident)


def test_expired_and_duplicate_approvals_rejected() -> None:
    incident = planned()
    approve(incident, incident.remediation.id, "sre")
    with pytest.raises(ConflictError):
        approve(incident, incident.remediation.id, "sre")
    incident.remediation.expires_at = now() - timedelta(seconds=1)
    with pytest.raises(ConflictError):
        authorize(incident)


def test_cross_incident_approval_cannot_be_reused() -> None:
    first, second = planned(), planned()
    approve(first, first.remediation.id, "sre")
    second.approvals = first.approvals
    second.remediation.status = "approved"
    with pytest.raises(ConflictError):
        authorize(second)


@pytest.mark.parametrize("params", [{"revision":"api-v1","expected_revision":"api-v2","shell":"x"}, {"revision":"; shutdown", "expected_revision":"api-v2"}])
def test_parameters_cannot_smuggle_commands(params: dict[str, str]) -> None:
    action = RemediationAction(capability="rollback_demo_revision", service_id="orders-api", parameters=params)
    with pytest.raises(ConflictError):
        validate_action(action, "orders-api")


def test_risk_cannot_be_downgraded() -> None:
    action = RemediationAction(capability="restart_demo_service", service_id="orders-api", risk=Risk.READ_ONLY)
    with pytest.raises(ConflictError):
        validate_action(action, "orders-api")
