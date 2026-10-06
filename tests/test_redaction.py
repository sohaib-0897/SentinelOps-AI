from sentinelops.domain.models import LogEntry
from sentinelops.security.redaction import redact


def test_common_secrets_are_redacted_before_persistence() -> None:
    entry = LogEntry(message="password=example-private-value api_key=example-token-value Authorization: Bearer abcdefghijk")
    assert "example-private" not in entry.message
    assert "abcdefghijk" not in entry.message
    assert entry.message.count("[REDACTED]") == 3


def test_private_keys_and_operational_text() -> None:
    assert redact("-----BEGIN PRIVATE KEY-----\nexample\n-----END PRIVATE KEY-----") == "[REDACTED]"
    assert redact("PostgreSQL connection timeout") == "PostgreSQL connection timeout"
