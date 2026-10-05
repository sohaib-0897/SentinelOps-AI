import re
from typing import Any

from sentinelops.providers.gcp.common import client, cloud_call, require_project


def crc32c(data: bytes) -> int:
    checksum = 0xFFFFFFFF
    for value in data:
        checksum ^= value
        for _ in range(8):
            checksum = (checksum >> 1) ^ (0x82F63B78 if checksum & 1 else 0)
    return checksum ^ 0xFFFFFFFF


class GCPSecretManager:
    def __init__(self, project: str, sdk: Any = None) -> None:
        require_project(project)
        self.project = project
        self.sdk = sdk if sdk is not None else client("google.cloud.secretmanager","SecretManagerServiceClient")

    async def access(self, secret_id: str, version: str = "latest") -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", secret_id) or not re.fullmatch(r"latest|[0-9]+", version):
            raise ValueError("Invalid secret identifier/version")
        name = f"projects/{self.project}/secrets/{secret_id}/versions/{version}"
        response = await cloud_call(lambda:self.sdk.access_secret_version(request={"name":name}))
        payload: bytes = response.payload.data
        if crc32c(payload) != response.payload.data_crc32c:
            raise ValueError("Secret payload integrity check failed")
        # Callers must never log this returned value.
        return payload.decode("utf-8")
