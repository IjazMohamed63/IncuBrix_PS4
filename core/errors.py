from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Standardized shared error codes per IncuBrix Appendix A specification."""
    DEST_SPEC_VIOLATION = "DEST_SPEC_VIOLATION"
    DEST_RULE_FREQUENCY_CAP = "DEST_RULE_FREQUENCY_CAP"
    CONNECTION_AUTH_EXPIRED = "CONNECTION_AUTH_EXPIRED"
    PLATFORM_RATE_LIMIT = "PLATFORM_RATE_LIMIT"
    PLATFORM_QUOTA_EXHAUSTED = "PLATFORM_QUOTA_EXHAUSTED"
    PLATFORM_CONTENT_REJECTED = "PLATFORM_CONTENT_REJECTED"
    PLATFORM_UNAVAILABLE = "PLATFORM_UNAVAILABLE"
    CONNECTOR_DISABLED = "CONNECTOR_DISABLED"

    # General validation / system fallback
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INVALID_MANIFEST = "INVALID_MANIFEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"


# Map each error code to its standard retryability property per spec
RETRYABLE_MAP: Dict[ErrorCode, bool] = {
    ErrorCode.DEST_SPEC_VIOLATION: False,
    ErrorCode.DEST_RULE_FREQUENCY_CAP: True,      # Retry later after window
    ErrorCode.CONNECTION_AUTH_EXPIRED: False,     # Requires reconnection
    ErrorCode.PLATFORM_RATE_LIMIT: True,          # Retry after backoff
    ErrorCode.PLATFORM_QUOTA_EXHAUSTED: True,     # Retry next window
    ErrorCode.PLATFORM_CONTENT_REJECTED: False,   # Content invalid
    ErrorCode.PLATFORM_UNAVAILABLE: True,         # Retry up to 5 times
    ErrorCode.CONNECTOR_DISABLED: False,          # Disabled by kill switch
    ErrorCode.INTERNAL_ERROR: False,
    ErrorCode.NOT_FOUND: False,
    ErrorCode.INVALID_MANIFEST: False,
    ErrorCode.VALIDATION_ERROR: False,
}


class IncuBrixError(Exception):
    """Base exception for all IncuBrix errors formatted to standard contract."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        retryable: Optional[bool] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable if retryable is not None else RETRYABLE_MAP.get(code, False)
        self.details = details or {}
        self.status_code = status_code

    def to_dict(self) -> Dict[str, Any]:
        """Produce the exact JSON response body required by the specification."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            }
        }


class ConnectorDisabledError(IncuBrixError):
    def __init__(self, connector_key: str):
        super().__init__(
            code=ErrorCode.CONNECTOR_DISABLED,
            message=f"Connector '{connector_key}' is disabled via kill switch.",
            retryable=False,
            details={"connector_key": connector_key},
            status_code=403,
        )


class DestinationSpecViolationError(IncuBrixError):
    def __init__(self, message: str, violations: list[str]):
        super().__init__(
            code=ErrorCode.DEST_SPEC_VIOLATION,
            message=message,
            retryable=False,
            details={"violations": violations},
            status_code=422,
        )


class PlatformRateLimitError(IncuBrixError):
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            code=ErrorCode.PLATFORM_RATE_LIMIT,
            message=message,
            retryable=True,
            details={"retry_after_seconds": retry_after} if retry_after else {},
            status_code=429,
        )


class PlatformUnavailableError(IncuBrixError):
    def __init__(self, message: str, consecutive_failures: int = 1):
        super().__init__(
            code=ErrorCode.PLATFORM_UNAVAILABLE,
            message=message,
            retryable=consecutive_failures < 5,
            details={"consecutive_failures": consecutive_failures},
            status_code=503,
        )


class ConnectionAuthExpiredError(IncuBrixError):
    def __init__(self, message: str = "Platform authentication token has expired or been revoked."):
        super().__init__(
            code=ErrorCode.CONNECTION_AUTH_EXPIRED,
            message=message,
            retryable=False,
            details={"action_required": "reconnect"},
            status_code=401,
        )


class PlatformContentRejectedError(IncuBrixError):
    def __init__(self, message: str, platform_reason: Optional[str] = None):
        super().__init__(
            code=ErrorCode.PLATFORM_CONTENT_REJECTED,
            message=message,
            retryable=False,
            details={"platform_reason": platform_reason} if platform_reason else {},
            status_code=422,
        )
