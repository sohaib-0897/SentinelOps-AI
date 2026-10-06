from sentinelops.config import Settings
from sentinelops.runtime import Runtime
from sentinelops.streaming import stream_events


class Connection:
    async def is_disconnected(self) -> bool:
        return False


async def test_stream_reconnect_snapshot_and_cleanup() -> None:
    runtime = Runtime(Settings(app_env="test", _env_file=None))
    stream = stream_events(runtime, Connection(), heartbeat=.01)
    assert "event: connected" in await anext(stream)
    assert len(runtime.bus.subscribers) == 1
    await runtime.bus.publish({"type":"EvidenceCollected", "incident_id":"x"})
    event = await anext(stream)
    assert "id: 1" in event and "EvidenceCollected" in event
    assert "heartbeat" in await anext(stream)
    await stream.aclose()
    assert not runtime.bus.subscribers


async def test_stream_filters_other_incidents() -> None:
    runtime = Runtime(Settings(app_env="test", _env_file=None))
    stream = stream_events(runtime, Connection(), incident_id="wanted", heartbeat=.01)
    await anext(stream)
    await runtime.bus.publish({"type":"update", "incident_id":"other"})
    await runtime.bus.publish({"type":"update", "incident_id":"wanted"})
    assert "wanted" in await anext(stream)
    await stream.aclose()
