from sentinelops.detection import detect_incident
from sentinelops.simulation import materialize


def test_sustained_threshold_and_deduplication() -> None:
    metrics = materialize("bad-deployment").metrics
    assert detect_incident(metrics[:9], []) is None
    incident = detect_incident(metrics, [])
    assert incident
    assert detect_incident(metrics, [incident]) is None


def test_healthy_system_never_creates_incident() -> None:
    assert detect_incident(materialize("healthy").metrics, []) is None
