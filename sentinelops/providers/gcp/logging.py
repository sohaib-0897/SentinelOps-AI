import hashlib
import json
from datetime import timedelta
from typing import Any

from sentinelops.domain.models import LogEntry, now
from sentinelops.providers.gcp.common import client, cloud_call, require_project


class GCPLoggingProvider:
    def __init__(self, project: str, sdk: Any = None) -> None:
        require_project(project)
        self.project = project
        self.sdk = sdk if sdk is not None else client("google.cloud.logging", "Client", project=project)

    async def search_logs(self, service_id: str, query: str = "", limit: int = 100) -> list[LogEntry]:
        if not 1 <= limit <= 600:
            raise ValueError("Log result limit must be 1–600")
        clauses = ["resource.type=\"cloud_run_revision\"", f"resource.labels.service_name={json.dumps(service_id)}", f"timestamp>={json.dumps((now()-timedelta(minutes=30)).isoformat())}"]
        if query:
            clauses.append(f"SEARCH({json.dumps(query)})")
        entries = await cloud_call(lambda: list(self.sdk.list_entries(resource_names=[f"projects/{self.project}"], filter_=" AND ".join(clauses), page_size=min(limit, 100), max_results=limit, order_by="timestamp asc")))
        result = []
        for entry in entries:
            payload = entry.payload
            message = str(payload.get("message", "Structured application log")) if isinstance(payload, dict) else str(payload)
            severity = str(entry.severity).upper()
            stable_id = hashlib.sha256(f"{self.project}:{service_id}:{entry.timestamp}:{message}".encode()).hexdigest()
            result.append(LogEntry(id=stable_id, timestamp=entry.timestamp or now(), service_id=service_id, revision=entry.resource.labels.get("revision_name", "unknown"), severity="ERROR" if severity in {"ERROR", "CRITICAL", "ALERT", "EMERGENCY"} else "WARNING" if severity == "WARNING" else "INFO", message=message[:4000]))
        return result
