import json
import re
from typing import Any

from sentinelops.providers.events import DomainEvent
from sentinelops.providers.gcp.common import (
    CloudConfigurationError,
    client,
    cloud_call,
    require_project,
)


def table_name(project: str, dataset: str, table: str) -> str:
    require_project(project)
    if not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", name) for name in (dataset, table)):
        raise ValueError("Invalid BigQuery dataset/table identifier")
    return f"{project}.{dataset}.{table}"


class BigQueryAnalyticsProvider:
    def __init__(self, project: str, dataset: str, sdk: Any = None) -> None:
        self.table = table_name(project,dataset,"domain_events")
        self.sdk = sdk if sdk is not None else client("google.cloud.bigquery","Client",project=project)

    async def record_event(self, event: dict[str, Any]) -> None:
        validated = DomainEvent.model_validate(event)
        row = {"event_id":validated.id, "timestamp":validated.timestamp.isoformat(), "event_type":validated.type, "incident_id":validated.incident_id, "payload":json.dumps(validated.data)}
        errors = await cloud_call(lambda: self.sdk.insert_rows_json(self.table,[row],row_ids=[validated.id]))
        if errors:
            raise CloudConfigurationError("BigQuery rejected an event; verify table schema and writer permissions")
