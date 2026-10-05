import importlib
from typing import Any

from sentinelops.providers.gcp.common import CloudConfigurationError


class CloudSQLConnectionFactory:
    """Passwordless IAM database authentication for PostgreSQL via the Cloud SQL connector."""
    def __init__(self, instance: str, user: str, database: str, sdk: Any = None) -> None:
        if instance.count(":") != 2 or not user or not database:
            raise CloudConfigurationError("Set CLOUD_SQL_INSTANCE, CLOUD_SQL_USER and CLOUD_SQL_DATABASE")
        self.instance, self.user, self.database = instance,user,database
        self.connector = sdk

    async def connect(self) -> Any:
        if self.connector is None:
            module = importlib.import_module("google.cloud.sql.connector")
            self.connector = await module.create_async_connector()
        return await self.connector.connect_async(self.instance,"asyncpg",user=self.user,db=self.database,enable_iam_auth=True)

    async def close(self) -> None:
        if self.connector:
            await self.connector.close_async()
