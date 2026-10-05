import pytest

from sentinelops.providers.local import LocalTelemetryProvider


async def test_telemetry_contract_and_snapshot() -> None:
    provider = LocalTelemetryProvider()
    provider.append(provider.healthy_sample())
    assert len(await provider.get_metric_series("orders-api")) == 1
    assert (await provider.get_service_health("orders-api")).healthy
    restored = LocalTelemetryProvider()
    restored.restore(provider.snapshot())
    assert restored.metrics == provider.metrics
    with pytest.raises(ValueError):
        await provider.search_logs("unknown")
