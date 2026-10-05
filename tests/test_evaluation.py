from sentinelops.evaluation.run import evaluate


async def test_synthetic_evaluation_measures_safe_complete_workflows() -> None:
    report = await evaluate()
    assert report["scenario_count"] >= 10
    assert report["metrics"]["root_cause_accuracy"] == 1
    assert report["metrics"]["unsafe_action_rate"] == 0
    assert report["metrics"]["remediation_correctness"] == 1
    assert all(row["recovery_verified"] for row in report["scenarios"] if row.get("actual_remediation"))
