import io
import json
import logging
import re
from pathlib import Path
import pytest

from core.logging import SECRET_PATTERNS, StructuredJsonFormatter, redact_secrets

TEST_SECRETS = [
    "Bearer super_secret_bearer_token_12345678",
    "api_key: ak_test_live_secret_key_88888888",
    "secret: top_secret_vault_password_9999",
    "token: bot_token_secret_abcdef123456",
    "whsec_98f12a34b56c78d901e23f45a67b89c0",
]


def test_redact_secrets_comprehensive():
    """Verify all defined sensitive secret patterns are sanitized."""
    for secret in TEST_SECRETS:
        redacted = redact_secrets(secret)
        assert "[REDACTED]" in redacted
        # Extract secret value and assert it is not leaked
        parts = re.split(r'[:\s]+', secret)
        secret_val = parts[-1]
        assert secret_val not in redacted, f"Secret value {secret_val} was leaked in redacted text: {redacted}"


def test_logger_formatter_redacts_exceptions_and_extra():
    """Verify StructuredJsonFormatter redacts secrets in exception traces and extra context."""
    formatter = StructuredJsonFormatter()

    try:
        raise ValueError("Failed connecting with password: database_super_password_4321")
    except Exception:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="secure_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=25,
        msg="Error authenticating with Bearer jwt_secret_token_12345678",
        args=(),
        exc_info=exc_info,
    )
    record.extra = {"api_key": "ak_extra_secret_key_999999"}

    formatted = formatter.format(record)
    log_json = json.loads(formatted)

    assert "jwt_secret_token_12345678" not in log_json["message"]
    assert "[REDACTED]" in log_json["message"]
    assert "database_super_password_4321" not in log_json["exception"]
    assert "[REDACTED]" in log_json["exception"]
    assert "ak_extra_secret_key_999999" not in str(log_json.get("api_key"))


def test_repo_scan_for_unredacted_secrets():
    """Scans codebase files for committed production secrets or hardcoded live tokens."""
    repo_root = Path(__file__).resolve().parent.parent.parent

    # File extensions to inspect
    target_extensions = {".py", ".yaml", ".json", ".env.example"}
    ignored_dirs = {".git", ".venv", "__pycache__", ".pytest_cache"}

    # Pattern for suspected high-entropy production tokens
    high_entropy_patterns = [
        re.compile(r'(?i)ghp_[A-Za-z0-9]{36}'),  # GitHub personal access tokens
        re.compile(r'(?i)sk_live_[A-Za-z0-9]{24,}'),  # Stripe live keys
        re.compile(r'(?i)aws_secret_access_key\s*=\s*[A-Za-z0-9/\+=]{40}'),  # AWS secret keys
    ]

    violations = []
    for path in repo_root.rglob("*"):
        if any(ignored in path.parts for ignored in ignored_dirs):
            continue
        if path.suffix in target_extensions and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                for pattern in high_entropy_patterns:
                    matches = pattern.findall(content)
                    if matches:
                        violations.append(f"{path.relative_to(repo_root)}: contains suspected secret {matches}")
            except Exception:
                continue

    assert len(violations) == 0, f"Found unredacted production secrets in repository: {violations}"
