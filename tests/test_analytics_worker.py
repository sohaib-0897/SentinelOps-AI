from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from sentinelops.analytics_worker import AnalyticsConsumer
from sentinelops.providers.events import DomainEvent


async def test_ack_only_after_success_and_preserve_event_id() -> None:
    event = DomainEvent(type="IncidentResolved",incident_id="incident-1")
    sdk = MagicMock()
    sdk.pull.return_value.received_messages = [SimpleNamespace(ack_id="success",message=SimpleNamespace(data=event.model_dump_json().encode())),SimpleNamespace(ack_id="invalid",message=SimpleNamespace(data=b"not-json"))]
    analytics = MagicMock(record_event=AsyncMock())
    consumer = AnalyticsConsumer("test-project","analytics",analytics,sdk)
    assert await consumer.drain_once() == {"accepted":1,"retry_pending":1}
    assert analytics.record_event.call_args.args[0]["id"] == event.id
    assert sdk.acknowledge.call_args.kwargs["request"]["ack_ids"] == ["success"]
    analytics.record_event.side_effect = RuntimeError("BigQuery unavailable")
    sdk.reset_mock()
    assert (await consumer.drain_once())["retry_pending"] == 2
    sdk.acknowledge.assert_not_called()
    with pytest.raises(ValueError):
        await consumer.drain_once(1000)


async def test_duplicate_delivery_keeps_stable_id_and_oversize_is_not_acked() -> None:
    event = DomainEvent(type="IncidentResolved")
    sdk = MagicMock()
    sdk.pull.return_value.received_messages = [
        SimpleNamespace(ack_id=ack, message=SimpleNamespace(data=event.model_dump_json().encode()))
        for ack in ["first", "duplicate"]
    ] + [SimpleNamespace(ack_id="large", message=SimpleNamespace(data=b"x" * 1000001))]
    analytics = MagicMock(record_event=AsyncMock())
    result = await AnalyticsConsumer("test-project", "analytics", analytics, sdk).drain_once()
    assert result == {"accepted": 2, "retry_pending": 1}
    assert [call.args[0]["id"] for call in analytics.record_event.call_args_list] == [event.id, event.id]
    assert sdk.acknowledge.call_args.kwargs["request"]["ack_ids"] == ["first", "duplicate"]
