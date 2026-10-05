import pytest

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import RemediationAction
from sentinelops.providers.remediation import LocalRemediationProvider
from sentinelops.simulation import materialize


async def test_rollback_restores_known_healthy_revision() -> None:
    telemetry = materialize("bad-deployment")
    action = RemediationAction(capability="rollback_demo_revision", service_id="orders-api", parameters={"revision":"api-v1", "expected_revision":"api-v2"})
    result = await LocalRemediationProvider(telemetry).execute(action)
    assert result["simulated"]
    assert telemetry.service.revision == "api-v1"
    assert all(m.error_rate < .01 for m in telemetry.metrics[-5:])
    with pytest.raises(ConflictError):
        await LocalRemediationProvider(telemetry).execute(action)


async def test_unknown_revision_cannot_be_targeted() -> None:
    telemetry = materialize("bad-deployment")
    action = RemediationAction(capability="rollback_demo_revision", service_id="orders-api", parameters={"revision":"unknown", "expected_revision":"api-v2"})
    with pytest.raises(ConflictError):
        await LocalRemediationProvider(telemetry).execute(action)
