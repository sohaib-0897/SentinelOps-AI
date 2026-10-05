"""Bounded Cloud Run job entry points; production identities use ADC and IAM."""
import argparse
import asyncio
import os
from typing import Any

import httpx

from sentinelops.config import Settings
from sentinelops.ingestion import TelemetryBatch
from sentinelops.providers.contracts import DeploymentProvider, LogProvider, MetricsProvider


async def collect(logs: LogProvider, metrics: MetricsProvider, deployments: DeploymentProvider) -> TelemetryBatch:
    observations, entries, revisions, service = await asyncio.gather(metrics.get_metric_series("orders-api", 120), logs.search_logs("orders-api", limit=200), deployments.get_recent_deployments("orders-api"), deployments.get_service_health("orders-api"))
    return TelemetryBatch(metrics=observations, logs=entries, deployments=revisions, service=service)


async def api_headers(client: httpx.AsyncClient, audience: str, operator_token: str) -> dict[str, str]:
    headers = {"Authorization":f"Bearer {operator_token}"} if operator_token else {}
    if audience:
        response = await client.get("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity", params={"audience":audience,"format":"full"}, headers={"Metadata-Flavor":"Google"})
        response.raise_for_status()
        headers["X-Serverless-Authorization"] = "Bearer " + response.text
    return headers


async def poll_once(settings: Settings, api_url: str, audience: str = "") -> dict[str, Any]:
    from sentinelops.providers.gcp.cloud_run import CloudRunDeploymentProvider
    from sentinelops.providers.gcp.logging import GCPLoggingProvider
    from sentinelops.providers.gcp.monitoring import GCPMonitoringMetricsProvider
    batch = await collect(GCPLoggingProvider(settings.gcp_project_id),GCPMonitoringMetricsProvider(settings.gcp_project_id),CloudRunDeploymentProvider(settings.gcp_project_id,settings.gcp_region))
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(api_url.rstrip("/")+"/api/v1/telemetry", json=batch.model_dump(mode="json"),headers=await api_headers(client,audience,settings.operator_token))
        response.raise_for_status()
        return dict(response.json())


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    if args.interval < 10:
        parser.error("Polling interval must be at least ten seconds")
    settings = Settings()
    while True:
        try:
            result = await poll_once(settings,os.getenv("API_BASE_URL","http://127.0.0.1:8000"),os.getenv("API_AUTH_AUDIENCE",""))
            print(f"Telemetry accepted: {result['accepted_metrics']} samples")
        except Exception:
            print("Telemetry poll failed safely; check worker configuration and IAM")
            if args.once:
                raise SystemExit(1) from None
        if args.once:
            return
        await asyncio.sleep(args.interval)


if __name__ == "__main__":
    asyncio.run(main())
