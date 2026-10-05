import pytest
from pydantic import ValidationError

from sentinelops.domain.models import Hypothesis, Incident, MetricPoint, RemediationAction


def test_strict_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Incident(title="test", shell="rm -rf")


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan")])
def test_confidence_is_bounded(value: float) -> None:
    with pytest.raises(ValidationError):
        Hypothesis(cause="x", description="x", confidence=value)


def test_capabilities_are_allowlisted() -> None:
    with pytest.raises(ValidationError):
        RemediationAction(capability="execute_shell", service_id="orders-api")


def test_metrics_reject_unbounded_simulation() -> None:
    with pytest.raises(ValidationError):
        MetricPoint(error_rate=2, latency_ms=-1, cpu=0, memory=0, db_connections=0, requests=1)
