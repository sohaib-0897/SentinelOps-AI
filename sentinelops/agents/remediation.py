from datetime import timedelta

from sentinelops.agents.common import AgentContext
from sentinelops.domain.models import RemediationAction, RemediationPlan, Risk, now
from sentinelops.tools.operations import ServiceQuery


class RemediationAgent:
    async def run(self, context: AgentContext) -> None:
        root = context.incident.root_cause
        if not root or root.confidence < .7:
            context.activity("REMEDIATION", "Insufficient evidence for a safe remediation proposal")
            return
        await context.tools.retrieve_runbook(root.cause)
        parameters: dict[str, str] = {}
        if root.cause in {"bad_deployment", "memory_regression", "configuration_regression"}:
            deployments = await context.tools.get_recent_deployments(ServiceQuery(service_id=context.incident.service_id))
            if not deployments:
                context.activity("REMEDIATION", "No known previous revision; rollback proposal withheld")
                return
            capability = "rollback_demo_revision"
            parameters = {"revision": deployments[-1].previous_revision, "expected_revision": deployments[-1].revision}
            summary = f"Rollback {deployments[-1].revision} to known healthy {parameters['revision']}"
        elif root.cause in {"database_exhaustion", "traffic_spike", "redis_saturation", "latency_degradation"}:
            capability = "simulate_scale_up"
            parameters = {"instances": "2"}
            summary = "Simulate bounded capacity recovery (local demonstration)"
        else:
            capability = "restart_demo_service"
            summary = "Restart the local demo service through its controlled interface"
        action = RemediationAction.model_validate({"capability": capability, "service_id": context.incident.service_id, "risk": Risk.PRIVILEGED, "parameters": parameters})
        context.incident.remediation = RemediationPlan(summary=summary, actions=[action], expires_at=now() + timedelta(minutes=30))
        context.activity("REMEDIATION", summary + "; human approval required")
