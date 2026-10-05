import pytest

from sentinelops.providers.local import LocalTelemetryProvider
from sentinelops.simulation import SimulationEngine, materialize, scenarios


@pytest.mark.parametrize("name", list(scenarios()))
def test_scenarios_are_safe_and_realistic(name: str) -> None:
    provider = materialize(name)
    assert len(provider.metrics) == 14
    assert len(provider.logs) == 6
    assert provider.metrics[0].error_rate < .01
    assert provider.metrics[-1].timestamp > provider.metrics[0].timestamp


def test_deployment_precedes_degradation_by_37_seconds() -> None:
    provider = materialize("bad-deployment")
    assert (provider.metrics[8].timestamp - provider.deployments[0].timestamp).total_seconds() == 37
    assert provider.metrics[-1].error_rate == .18


def test_pause_does_not_advance_clock() -> None:
    engine = SimulationEngine(LocalTelemetryProvider())
    engine.start("bad-deployment")
    engine.paused = True
    engine.tick()
    assert engine.step == 0
