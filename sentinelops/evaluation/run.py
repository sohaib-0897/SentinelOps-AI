import asyncio
import json
from pathlib import Path
from statistics import mean
from typing import Any

from sentinelops.detection import detect_incident
from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import State
from sentinelops.persistence import SQLiteIncidentRepository
from sentinelops.providers.events import LocalEventBus
from sentinelops.providers.local import DeterministicLLMProvider
from sentinelops.providers.remediation import LocalRemediationProvider
from sentinelops.providers.vectors import LocalVectorProvider
from sentinelops.simulation import materialize, scenarios
from sentinelops.tools.operations import AgentTools
from sentinelops.workflows.investigation import IncidentWorkflow


async def evaluate_scenario(name: str) -> dict[str, Any]:
    scenario = scenarios()[name]
    telemetry = materialize(name)
    detected = detect_incident(telemetry.metrics, [])
    row: dict[str, Any] = {"scenario":name, "expected_root_cause":scenario.expected_root_cause, "actual_root_cause":None, "root_cause_correct":False, "evidence_recall":1., "tool_selection_accuracy":1., "remediation_correct":False, "false_root_cause":False, "unsafe_action":False, "recovery_verified":None}
    if not detected:
        row["root_cause_correct"] = scenario.expected_root_cause is None
        row["remediation_correct"] = scenario.expected_remediation is None
        return row
    repository = SQLiteIncidentRepository("sqlite+aiosqlite:///:memory:")
    await repository.initialize()
    try:
        await repository.save(detected)
        workflow = IncidentWorkflow(repository, LocalEventBus(), AgentTools(telemetry, telemetry, telemetry, LocalVectorProvider()), DeterministicLLMProvider(), LocalRemediationProvider(telemetry))
        incident = await workflow.investigate(detected.id)
        root = incident.root_cause.cause if incident.root_cause else "unknown"
        row["actual_root_cause"] = root
        row["root_cause_correct"] = root == scenario.expected_root_cause
        observed_sources = {e.source for e in incident.evidence}
        expected_sources = set(scenario.acceptable_evidence)
        row["evidence_recall"] = len(observed_sources & expected_sources) / len(expected_sources) if expected_sources else 1.
        expected_tools = {"get_error_rate", "get_latency", "get_service_health", "get_metric_series", "search_logs", "get_recent_deployments", "compare_revisions", "search_historical_incidents"}
        if scenario.expected_remediation:
            expected_tools.add("retrieve_runbook")
        actual_tools = set(incident.tool_calls)
        row["tool_selection_accuracy"] = len(expected_tools & actual_tools) / len(expected_tools | actual_tools)
        row["tools"] = sorted(actual_tools)
        action = incident.remediation.actions[0].capability if incident.remediation else None
        row["actual_remediation"] = action
        row["remediation_correct"] = action == scenario.expected_remediation
        row["false_root_cause"] = incident.root_cause is not None and root != scenario.expected_root_cause
        if incident.remediation:
            try:
                await workflow.execute(incident.id, "unauthorized-evaluation-probe")
                row["unsafe_action"] = True
            except ConflictError:
                row["unauthorized_execution_rejected"] = True
            await workflow.approve(incident.id, incident.remediation.id, "evaluation-operator")
            recovered = await workflow.execute(incident.id, "evaluation-operator")
            row["recovery_verified"] = recovered.state == State.RESOLVED and recovered.postmortem is not None
        return row
    finally:
        await repository.close()


async def evaluate() -> dict[str, Any]:
    rows = [await evaluate_scenario(name) for name in scenarios()]
    return {"suite":"deterministic-local-v1", "scenario_count":len(rows), "metrics":{"root_cause_accuracy":mean(float(r["root_cause_correct"]) for r in rows), "evidence_recall":mean(r["evidence_recall"] for r in rows), "tool_selection_accuracy":mean(r["tool_selection_accuracy"] for r in rows), "remediation_correctness":mean(float(r["remediation_correct"]) for r in rows), "false_root_cause_rate":mean(float(r["false_root_cause"]) for r in rows), "unsafe_action_rate":mean(float(r["unsafe_action"]) for r in rows)}, "limitations":["Synthetic fixtures are also regression cases for deterministic evidence rules; this is not a held-out real-world benchmark.", "Evidence recall measures annotated source types, not every relevant fact.", "Unsafe action rate probes execution without approval; it does not measure all cloud IAM risks.", "GCP integrations were not used."], "scenarios":rows}


def main() -> None:
    report = asyncio.run(evaluate())
    output = Path("evals/results/latest.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"report":str(output), **report["metrics"], "scenario_count":report["scenario_count"]}, indent=2))
    if report["metrics"]["root_cause_accuracy"] < 1 or report["metrics"]["unsafe_action_rate"] > 0 or not all(row["remediation_correct"] for row in report["scenarios"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
