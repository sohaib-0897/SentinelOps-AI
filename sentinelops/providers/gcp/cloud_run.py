import itertools
from typing import Any

from sentinelops.domain.lifecycle import ConflictError
from sentinelops.domain.models import Deployment, RemediationAction, Service, now
from sentinelops.providers.gcp.common import client, cloud_call, require_project
from sentinelops.security.approval import validate_action


class CloudRunDeploymentProvider:
    def __init__(self, project: str, region: str, services_sdk: Any = None, revisions_sdk: Any = None, allowed_services: frozenset[str] = frozenset({"orders-api"})) -> None:
        require_project(project)
        self.project, self.region = project, region
        self.allowed_services = allowed_services
        self.services_sdk = services_sdk if services_sdk is not None else client("google.cloud.run_v2", "ServicesClient")
        self.revisions_sdk = revisions_sdk if revisions_sdk is not None else client("google.cloud.run_v2", "RevisionsClient")

    def name(self, service_id: str) -> str:
        if service_id not in self.allowed_services:
            raise ConflictError("Cloud Run service is not allow-listed")
        return f"projects/{self.project}/locations/{self.region}/services/{service_id}"

    async def get_recent_deployments(self, service_id: str) -> list[Deployment]:
        name = self.name(service_id)
        revisions = await cloud_call(lambda: list(itertools.islice(self.revisions_sdk.list_revisions(request={"parent":name, "page_size":100}), 100)))
        ordered = sorted(revisions, key=lambda r: r.create_time)
        result = []
        for index, revision in enumerate(ordered):
            if index == 0:
                continue
            previous = ordered[index-1]
            current_env = {e.name:e.value for container in revision.containers for e in container.env if e.value}
            previous_env = {e.name:e.value for container in previous.containers for e in container.env if e.value}
            changes = {key:"[REDACTED]" if any(s in key.lower() for s in ("secret","token","password","key")) else value for key,value in current_env.items() if previous_env.get(key) != value}
            result.append(Deployment(service_id=service_id, revision=revision.name.rsplit("/",1)[-1], previous_revision=previous.name.rsplit("/",1)[-1], timestamp=revision.create_time or now(), changes=changes, healthy=bool(revision.conditions) and any(int(c.state) == 4 for c in revision.conditions)))
        return result

    async def get_service_health(self, service_id: str) -> Service:
        name = self.name(service_id)
        service = await cloud_call(lambda: self.services_sdk.get_service(request={"name":name}))
        traffic = sorted(service.traffic_statuses, key=lambda t:t.percent, reverse=True)
        revision = traffic[0].revision if traffic else service.latest_ready_revision
        return Service(id=service_id, name=service_id, region=self.region, revision=revision.rsplit("/",1)[-1], healthy=int(service.terminal_condition.state) == 4 and not service.reconciling)

    async def rollback(self, action: RemediationAction) -> dict[str, Any]:
        validate_action(action, action.service_id)
        name = self.name(action.service_id)
        current = await cloud_call(lambda: self.services_sdk.get_service(request={"name":name}))
        traffic = sorted(current.traffic_statuses, key=lambda t:t.percent, reverse=True)
        serving = (traffic[0].revision if traffic else current.latest_ready_revision).rsplit("/",1)[-1]
        if current.reconciling or serving != action.parameters["expected_revision"]:
            raise ConflictError("Cloud Run serving revision changed or is reconciling")
        target = action.parameters["revision"]
        revision = await cloud_call(lambda: self.revisions_sdk.get_revision(request={"name":f"{name}/revisions/{target}"}))
        if not any(int(condition.state) == 4 for condition in revision.conditions):
            raise ConflictError("Target Cloud Run revision is not ready")
        request = {"service":{"name":name, "etag":current.etag, "traffic":[{"type_":"TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION", "revision":target, "percent":100}]}, "update_mask":{"paths":["traffic"]}}
        operation = await cloud_call(lambda: self.services_sdk.update_service(request=request))
        await cloud_call(lambda: operation.result(timeout=180))
        return {"revision":target, "simulated":False, "operation":"traffic_rollback"}


class CloudRunRemediationProvider:
    def __init__(self, deployments: CloudRunDeploymentProvider) -> None:
        self.deployments = deployments

    async def execute(self, action: RemediationAction) -> dict[str, Any]:
        if action.capability not in {"rollback_demo_revision", "change_demo_traffic_split"}:
            raise ConflictError("Only explicit revision traffic changes are supported by the GCP executor")
        return await self.deployments.rollback(action)
