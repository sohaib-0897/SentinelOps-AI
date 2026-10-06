from dataclasses import dataclass

from sentinelops.config import Settings
from sentinelops.providers.contracts import (
    DeploymentProvider,
    EventBus,
    LLMProvider,
    LogProvider,
    MetricsProvider,
    RemediationProvider,
    VectorSearchProvider,
)
from sentinelops.providers.events import LocalEventBus
from sentinelops.providers.local import DeterministicLLMProvider, LocalTelemetryProvider
from sentinelops.providers.remediation import LocalRemediationProvider
from sentinelops.providers.vectors import LocalVectorProvider


@dataclass
class Providers:
    logs: LogProvider
    metrics: MetricsProvider
    deployments: DeploymentProvider
    vectors: VectorSearchProvider
    llm: LLMProvider
    remediation: RemediationProvider
    events: EventBus


def build_providers(settings: Settings, local: LocalTelemetryProvider, bus: LocalEventBus) -> Providers:
    providers = Providers(local,local,local,LocalVectorProvider(),DeterministicLLMProvider(),LocalRemediationProvider(local, settings.demo_service_url if settings.connect_demo_service else None, settings.operator_token),bus)
    if settings.log_provider == "gcp":
        from sentinelops.providers.gcp.logging import GCPLoggingProvider
        providers.logs = GCPLoggingProvider(settings.gcp_project_id)
    if settings.metrics_provider == "gcp":
        from sentinelops.providers.gcp.monitoring import GCPMonitoringMetricsProvider
        providers.metrics = GCPMonitoringMetricsProvider(settings.gcp_project_id)
    if settings.deployment_provider == "gcp" or settings.remediation_provider == "gcp":
        from sentinelops.providers.gcp.cloud_run import (
            CloudRunDeploymentProvider,
            CloudRunRemediationProvider,
        )
        deployments = CloudRunDeploymentProvider(settings.gcp_project_id,settings.gcp_region)
        if settings.deployment_provider == "gcp":
            providers.deployments = deployments
        if settings.remediation_provider == "gcp":
            providers.remediation = CloudRunRemediationProvider(deployments, settings.remediation_service_account)
    if settings.vector_provider == "bigquery":
        from sentinelops.providers.gcp.vectors import BigQueryVectorProvider
        providers.vectors = BigQueryVectorProvider(settings.gcp_project_id,settings.bigquery_dataset)
    if settings.llm_provider == "vertex":
        from sentinelops.providers.gcp.vertex import GeminiVertexAIProvider
        providers.llm = GeminiVertexAIProvider(settings.gcp_project_id,settings.vertex_location,settings.gemini_model)
    if settings.llm_provider == "adk":
        from sentinelops.providers.gcp.adk import ADKExplanationProvider
        providers.llm = ADKExplanationProvider(settings.gcp_project_id, settings.vertex_location, settings.gemini_model)
    if settings.event_provider == "pubsub":
        from sentinelops.providers.gcp.pubsub import GCPPubSubEventBus, MirroredEventBus
        providers.events = MirroredEventBus(bus,GCPPubSubEventBus(settings.gcp_project_id,settings.pubsub_topic))
    return providers
