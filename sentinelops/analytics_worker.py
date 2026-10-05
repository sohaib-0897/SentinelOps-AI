"""Deliver Pub/Sub domain events to BigQuery with acknowledgement after persistence."""
import asyncio
import importlib
from typing import Any

from sentinelops.config import Settings
from sentinelops.domain.models import HistoricalIncident
from sentinelops.providers.events import DomainEvent
from sentinelops.providers.gcp.bigquery import BigQueryAnalyticsProvider
from sentinelops.providers.gcp.common import (
    CloudConfigurationError,
    client,
    cloud_call,
    require_project,
)
from sentinelops.providers.gcp.vectors import BigQueryVectorProvider


class AnalyticsConsumer:
    def __init__(self, project: str, subscription: str, analytics: BigQueryAnalyticsProvider, subscriber: Any = None, history: BigQueryVectorProvider | None = None) -> None:
        require_project(project)
        self.subscription = f"projects/{project}/subscriptions/{subscription}"
        self.analytics = analytics
        self.history = history
        self.subscriber = subscriber if subscriber is not None else client("google.cloud.pubsub_v1", "SubscriberClient")

    async def drain_once(self, limit: int = 50) -> dict[str, int]:
        if not 1 <= limit <= 100:
            raise ValueError("Batch size must be 1-100")
        try:
            # Scheduler retries are bounded separately; avoid the SDK's long default retry window.
            response = await cloud_call(lambda: self.subscriber.pull(request={"subscription":self.subscription,"max_messages":limit},timeout=15,retry=None))
        except CloudConfigurationError as error:
            deadline = importlib.import_module("google.api_core.exceptions").DeadlineExceeded
            if isinstance(error.__cause__, deadline):
                # No messages were received or acknowledged. This is not proof the queue is empty.
                return {"accepted":0,"retry_pending":0,"pull_timeouts":1}
            raise
        accepted: list[str] = []
        failed = 0
        for received in response.received_messages:
            try:
                if len(received.message.data) > 1000000:
                    raise ValueError("Oversized event")
                event = DomainEvent.model_validate_json(received.message.data)
                historical = None
                if event.type == "IncidentResolved" and "history" in event.data:
                    historical = HistoricalIncident.model_validate(event.data["history"])
                    if historical.id != event.incident_id or historical.outcome != "resolved":
                        raise ValueError("Historical event provenance does not match incident")
                await self.analytics.record_event(event.model_dump(mode="json"))
                if historical and self.history:
                    await self.history.seed([historical])
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
    consumer = AnalyticsConsumer(settings.gcp_project_id,settings.pubsub_subscription,BigQueryAnalyticsProvider(settings.gcp_project_id,settings.bigquery_dataset), history=BigQueryVectorProvider(settings.gcp_project_id, settings.bigquery_dataset))
    try:
        result = await consumer.drain_once()
        print(f"Analytics delivered: {result['accepted']}; pending retries: {result['retry_pending']}")
        if result.get("pull_timeouts"):
            print("Analytics pull deadline elapsed without a response; next scheduled run will retry")
        if result["retry_pending"]:
            raise SystemExit(1)
    finally:
        consumer.close()


if __name__ == "__main__":
    asyncio.run(main())
