from datetime import datetime

from sentinelops.agents.common import AgentContext
from sentinelops.domain.models import Deployment, Hypothesis, MetricPoint, RootCauseAnalysis


class RootCauseAgent:
    """Evidence rules determine causes; an LLM may explain but cannot invent the diagnosis."""

    async def run(self, context: AgentContext) -> None:
        incident = context.incident
        log_evidence = [e for e in incident.evidence if e.source == "logs"]
        metric_evidence = next((e for e in incident.evidence if "latest" in e.data), None)
        if not log_evidence or not metric_evidence:
            context.activity("ROOT CAUSE", "Insufficient independent evidence; diagnosis withheld")
            return
        point = MetricPoint.model_validate(metric_evidence.data["latest"])
        text = " ".join(str(entry["message"]) for e in log_evidence for entry in e.data.get("entries", [])).lower()
        onset = datetime.fromisoformat(metric_evidence.data["onset"])
        deployment_evidence = next((e for e in reversed(incident.evidence) if e.source == "deployments" and 0 <= (onset - e.timestamp).total_seconds() <= 300), None)
        supporting = [log_evidence[0].id, metric_evidence.id]
        cause = "unknown"
        score = .15
        description = "Metric degradation lacks a diagnostic signature. Gather more evidence."
        if "configuration regression" in text and deployment_evidence:
            cause, score, description = "configuration_regression", .92, "Changed upstream configuration coincides with connection failures"
        elif "memory pressure" in text and point.memory >= .9:
            cause, score, description = "memory_regression", .90, "Memory pressure and heap growth correlate with sustained resource exhaustion"
        elif "pool exhaustion" in text and (point.db_connections >= .9 or ("db_connections" not in point.available_metrics and point.error_rate >= .05)):
            if deployment_evidence:
                deployment = Deployment.model_validate(deployment_evidence.data)
                seconds = (onset - deployment.timestamp).total_seconds()
                cause, score, description = "bad_deployment", .94, f"Revision {deployment.revision} deployed {seconds:.0f}s before database pool exhaustion and HTTP errors"
            else:
                cause, score, description = "database_exhaustion", .89, "Pool acquisition timeouts corroborate database connection saturation"
        elif "redis saturation" in text and point.latency_ms >= 800:
            cause, score, description = "redis_saturation", .88, "Redis timeouts and queued connections corroborate cache saturation"
        elif "dependency timeout" in text and point.latency_ms >= 800:
            cause, score, description = "dependency_timeout", .88, "Upstream timeout logs corroborate dependency latency"
        elif "traffic spike" in text and point.cpu >= .95 and point.requests >= 1000:
            cause, score, description = "traffic_spike", .91, "Increased request volume and CPU saturation corroborate traffic overload"
        elif "application exception" in text and point.error_rate >= .05:
            cause, score, description = "application_errors", .85, "Application exceptions corroborate elevated HTTP errors"
        elif "latency degradation" in text and point.latency_ms >= 800:
            cause, score, description = "latency_degradation", .85, "Slow-request logs corroborate sustained latency degradation"
        if deployment_evidence and cause in {"bad_deployment", "configuration_regression", "memory_regression"}:
            supporting.append(deployment_evidence.id)
        supporting.extend(e.id for e in incident.evidence if e.source == "configuration" and cause in {"bad_deployment", "configuration_regression"})
        supporting.extend(e.id for e in incident.evidence if e.source == "history" and e.data.get("cause") == cause)
        cpu_evidence = next((e for e in incident.evidence if "cpu" in e.data), None)
        contradictions = [cpu_evidence.id] if cpu_evidence and "cpu" in point.available_metrics and point.cpu < .5 and cause == "bad_deployment" else []
        primary = Hypothesis(cause=cause, description=description, confidence=score, supporting_evidence=supporting if cause != "unknown" else [metric_evidence.id], contradicting_evidence=contradictions)
        alternatives = [Hypothesis(cause="database_exhaustion" if cause != "database_exhaustion" else "dependency_timeout", description="Alternative explanation requires independent confirmation", confidence=.42 if cause == "bad_deployment" else .12, supporting_evidence=[metric_evidence.id], contradicting_evidence=[log_evidence[0].id]), Hypothesis(cause="resource_saturation", description="Resource saturation considered; CPU and memory compared with baseline", confidence=.10, supporting_evidence=[metric_evidence.id], contradicting_evidence=[cpu_evidence.id] if cpu_evidence else [])]
        incident.hypotheses = sorted([primary, *alternatives], key=lambda h: h.confidence, reverse=True)
        if cause == "unknown":
            context.activity("ROOT CAUSE", "No supported root cause; automatic remediation withheld")
            return
        explanation = await context.llm.explain([e.model_dump(mode="json") for e in incident.evidence if e.id in supporting])
        incident.root_cause = RootCauseAnalysis(hypothesis_id=primary.id, cause=cause, confidence=score, explanation=description + ". " + explanation[:4000], evidence_ids=supporting)
        context.activity("ROOT CAUSE", f"{cause.replace('_', ' ').title()} ranked first with {score:.0%} evidence score")
