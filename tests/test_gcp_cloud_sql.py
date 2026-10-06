from unittest.mock import AsyncMock

from sentinelops.providers.gcp.cloud_sql import CloudSQLConnectionFactory


async def test_cloud_sql_uses_iam_without_password() -> None:
    sdk = AsyncMock()
    factory = CloudSQLConnectionFactory("test-project:us-central1:sentinelops","sentinelops-api@test-project.iam","sentinelops",sdk)
    await factory.connect()
    assert sdk.connect_async.call_args.kwargs["enable_iam_auth"] is True
    assert "password" not in sdk.connect_async.call_args.kwargs
    await factory.close()
    sdk.close_async.assert_awaited_once()
