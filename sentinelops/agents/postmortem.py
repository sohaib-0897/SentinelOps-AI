from sentinelops.agents.common import AgentContext
from sentinelops.domain.models import Postmortem, event_time


class PostmortemAgent:
    async def run(self, context: AgentContext) -> None:
        incident = context.incident
        root, verification, plan = incident.root_cause, incident.verification, incident.remediation
        if not root or not verification or not verification.recovered or not plan:
            raise ValueError("Postmortem requires a supported root cause and verified recovery")
        incident.postmortem = Postmortem(
            summary=f"{incident.title} resolved after approved remediation.",
            impact=f"{incident.service_id}: error rate reached {verification.before_error_rate:.1%}; p95 latency {verification.before_latency_ms:.0f}ms. Request counts are telemetry samples, not measured affected users.",
            timeline=sorted(incident.timeline, key=lambda event: event.timestamp),
            root_cause=f"{root.cause}: {root.explanation}",
            detection="Three consecutive unhealthy metric samples exceeded configured thresholds.",
            response="Triage, investigation, historical retrieval and evidence-backed diagnosis preceded approval.",
            remediation=plan.summary,
            what_worked=["Evidence preserved with source timestamps", "Approval bound to the exact remediation plan", "Recovery independently verified across five new samples"],
            what_failed=["Regression reached the service before deployment health gates caught it"],
            prevention=["Add canary health gates for latency and errors", "Validate database pool and dependency configuration at startup", "Test bounded resource capacity before rollout"],
            follow_up_actions=["SRE: add rollout abort thresholds", "Service owner: add regression test for the observed failure signature", "Platform: review alert thresholds and runbook"],
            generated_at=event_time(incident),
        )
        context.activity("POSTMORTEM", "Evidence-backed postmortem generated with timeline and follow-up actions")
