import json
import logging
from core.logging import StructuredJsonFormatter, redact_secrets


def test_redact_secrets_patterns():
    """Verify sensitive tokens and keys are redacted properly."""
    raw_1 = "Authorization: Bearer secret_token_xyz_123456789"
    redacted_1 = redact_secrets(raw_1)
    assert "[REDACTED]" in redacted_1
    assert "secret_token_xyz_123456789" not in redacted_1

    raw_2 = "api_key: ak_live_9876543210abcdef"
    assert "[REDACTED]" in redact_secrets(raw_2)

    raw_3 = "Received payload with secret: super_secret_pass_123"
    assert "[REDACTED]" in redact_secrets(raw_3)

    raw_4 = "Signature secret whsec_abcdef1234567890abcdef"
    assert "[REDACTED]" in redact_secrets(raw_4)


def test_structured_json_formatter():
    """Verify StructuredJsonFormatter outputs valid JSON and redacts messages."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Login with Bearer token_secret_abcdef123456",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert "token_secret_abcdef123456" not in parsed["message"]
    assert "[REDACTED]" in parsed["message"]
    assert "timestamp" in parsed
