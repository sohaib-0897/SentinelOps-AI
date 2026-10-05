"""Deliver Pub/Sub domain events to BigQuery with acknowledgement after persistence."""
import asyncio
from typing import Any

from sentinelops.config import Settings
from sentinelops.providers.events import DomainEvent
from sentinelops.providers.gcp.bigquery import BigQueryAnalyticsProvider
from sentinelops.providers.gcp.common import client, cloud_call, require_project


class AnalyticsConsumer:
    def __init__(self, project: str, subscription: str, analytics: BigQueryAnalyticsProvider, subscriber: Any = None) -> None:
        require_project(project)
        self.subscription = f"projects/{project}/subscriptions/{subscription}"
        self.analytics = analytics
        self.subscriber = subscriber if subscriber is not None else client("google.cloud.pubsub_v1", "SubscriberClient")

    async def drain_once(self, limit: int = 50) -> dict[str, int]:
        if not 1 <= limit <= 100:
            raise ValueError("Batch size must be 1-100")
        response = await cloud_call(lambda: self.subscriber.pull(request={"subscription":self.subscription,"max_messages":limit},timeout=15))
        accepted: list[str] = []
        failed = 0
        for received in response.received_messages:
            try:
                if len(received.message.data) > 1000000:
                    raise ValueError("Oversized event")
                event = DomainEvent.model_validate_json(received.message.data)
                await self.analytics.record_event(event.model_dump(mode="json"))
                accepted.append(received.ack_id)
            except Exception:
                failed += 1
        if accepted:
            await cloud_call(lambda: self.subscriber.acknowledge(request={"subscription":self.subscription,"ack_ids":accepted}))
        return {"accepted":len(accepted),"retry_pending":failed}

    def close(self) -> None:
        self.subscriber.close()


async def main() -> None:
    settings = Settings()
    consumer = AnalyticsConsumer(settings.gcp_project_id,settings.pubsub_subscription,BigQueryAnalyticsProvider(settings.gcp_project_id,settings.bigquery_dataset))
    try:
        result = await consumer.drain_once()
        print(f"Analytics delivered: {result['accepted']}; pending retries: {result['retry_pending']}")
        if result["retry_pending"]:
            raise SystemExit(1)
    finally:
        consumer.close()


if __name__ == "__main__":
    asyncio.run(main())
