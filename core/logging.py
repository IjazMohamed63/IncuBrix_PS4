import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variables for correlation tracking across async tasks
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id", default=None)

# Regular expressions to catch and redact sensitive strings in log messages
SECRET_PATTERNS = [
    re.compile(r'(?i)(bearer\s+)[A-Za-z0-9_\-\.]{10,}'),
    re.compile(r'(?i)(api[_-]?key[\s:=]+)[A-Za-z0-9_\-\.]{10,}'),
    re.compile(r'(?i)(secret[\s:=]+)[A-Za-z0-9_\-\.]{10,}'),
    re.compile(r'(?i)(token[\s:=]+)[A-Za-z0-9_\-\.]{10,}'),
    re.compile(r'(?i)(password[\s:=]+)[^\s,;]+'),
    re.compile(r'whsec_[a-zA-Z0-9]{16,}'),
]


def redact_secrets(text: str) -> str:
    """Redacts any sensitive tokens, API keys, or passwords from string."""
    if not isinstance(text, str):
        text = str(text)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(r'\1[REDACTED]' if r'\1' in pattern.pattern else '[REDACTED]', text)
    return text


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON with correlation ID and secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        # Base message formatting with redaction
        msg = record.getMessage()
        msg = redact_secrets(msg)

        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": msg,
            "X-Correlation-Id": correlation_id_ctx.get() or getattr(record, "correlation_id", None),
            "job_id": job_id_ctx.get() or getattr(record, "job_id", None),
        }

        # Include exception trace if present
        if record.exc_info:
            log_payload["exception"] = redact_secrets(self.formatException(record.exc_info))

        # Include extra attributes if provided
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            for k, v in record.extra.items():
                if k not in log_payload:
                    log_payload[k] = redact_secrets(str(v)) if isinstance(v, str) else v

        return json.dumps(log_payload)


def setup_logging(log_level: str = "INFO") -> None:
    """Configures root logger to use structured JSON logging to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger configured with structured output."""
    return logging.getLogger(name)
