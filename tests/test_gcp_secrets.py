from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from sentinelops.providers.gcp.secrets import GCPSecretManager, crc32c


async def test_secret_access_scopes_and_validates_resource() -> None:
    sdk = MagicMock()
    sdk.access_secret_version.return_value = SimpleNamespace(payload=SimpleNamespace(data=b"example-placeholder", data_crc32c=crc32c(b"example-placeholder")))
    provider = GCPSecretManager("test-project",sdk)
    assert await provider.access("operator-token") == "example-placeholder"
    assert sdk.access_secret_version.call_args.kwargs["request"]["name"] == "projects/test-project/secrets/operator-token/versions/latest"
    with pytest.raises(ValueError):
        await provider.access("../../different-project")
    sdk.access_secret_version.return_value.payload.data_crc32c = 0
    with pytest.raises(ValueError, match="integrity"):
        await provider.access("operator-token")


def test_crc32c_standard_vector() -> None:
    assert crc32c(b"123456789") == 0xE3069283
