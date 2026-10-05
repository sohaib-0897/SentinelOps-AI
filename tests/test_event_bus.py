from sentinelops.providers.events import LocalEventBus


async def test_subscriptions_cleanup_and_ordering() -> None:
    bus = LocalEventBus()
    async with bus.subscribe() as queue:
        await bus.publish({"type": "IncidentDetected"})
        assert (await queue.get())["sequence"] == 1
    assert not bus.subscribers


async def test_slow_subscriber_resynchronizes() -> None:
    bus = LocalEventBus(capacity=2)
    async with bus.subscribe() as queue:
        for _ in range(3):
            await bus.publish({"type": "metrics"})
        assert (await queue.get())["type"] == "resync"
        assert queue.empty()
