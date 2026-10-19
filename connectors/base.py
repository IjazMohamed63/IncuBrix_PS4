from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from connectors.schemas import (
    BuildAssistPackResponse,
    ConnectorManifest,
    ConnectionPayload,
    DeleteResponse,
    DestinationPayload,
    FetchMetricsResponse,
    GetStatusResponse,
    PublishResponse,
    RefreshAuthResponse,
    Rendition,
    ValidateResponse,
)
from core.errors import (
    ConnectionAuthExpiredError,
    ErrorCode,
    IncuBrixError,
    PlatformContentRejectedError,
    PlatformRateLimitError,
    PlatformUnavailableError,
)


class BaseConnector(ABC):
    """Abstract Base Class for all IncuBrix connectors.

    Connectors are purely stateless protocol adapters. They never write to
    the IncuBrix database and only communicate with external platforms.
    """

    def __init__(self, manifest: ConnectorManifest):
        self.manifest = manifest
        self.key = manifest.key

    async def execute_request(
        self,
        http_client: Optional[Any],
        method: str,
        url: str,
        **kwargs,
    ) -> Any:
        """Executes HTTP request, automatically routing http://test to mock platforms app."""
        if http_client:
            return await http_client.request(method, url, **kwargs)
        if url.startswith("http://test"):
            import httpx
            from mock_platforms.main import app as mock_app
            transport = httpx.ASGITransport(app=mock_app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, url, **kwargs)
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await client.request(method, url, **kwargs)

    @abstractmethod
    async def validate(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
    ) -> ValidateResponse:
        """Validates rendition formatting against destination and manifest specs."""
        raise NotImplementedError

    @abstractmethod
    async def publish(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        idempotency_key: str,
    ) -> PublishResponse:
        """Publishes content to the target destination platform."""
        raise NotImplementedError

    @abstractmethod
    async def get_status(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> GetStatusResponse:
        """Verifies if the published post is active and publicly live."""
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> DeleteResponse:
        """Deletes or unpublishes the specified post."""
        raise NotImplementedError

    async def fetch_metrics(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
        since: Optional[str] = None,
    ) -> FetchMetricsResponse:
        """Fetches engagement metrics. Optional capability."""
        raise IncuBrixError(
            code=ErrorCode.DEST_SPEC_VIOLATION,
            message=f"Connector '{self.key}' does not support fetch_metrics.",
            retryable=False,
            status_code=400,
        )

    async def refresh_auth(
        self,
        connection: ConnectionPayload,
    ) -> RefreshAuthResponse:
        """Refreshes expired or near-expiry authentication credentials. Optional capability."""
        raise IncuBrixError(
            code=ErrorCode.DEST_SPEC_VIOLATION,
            message=f"Connector '{self.key}' does not support refresh_auth.",
            retryable=False,
            status_code=400,
        )

    async def build_assist_pack(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
    ) -> BuildAssistPackResponse:
        """Constructs an assisted posting pack where automation is disallowed."""
        raise IncuBrixError(
            code=ErrorCode.DEST_SPEC_VIOLATION,
            message=f"Connector '{self.key}' does not support build_assist_pack.",
            retryable=False,
            status_code=400,
        )

    def map_http_status_to_error(
        self,
        status_code: int,
        response_text: str = "",
        headers: Optional[Dict[str, str]] = None,
    ) -> IncuBrixError:
        """Translates external HTTP status code to IncuBrix shared error code
        using the connector's manifest error_map, falling back to spec standards.
        """
        code_str = str(status_code)
        mapped_code_name = self.manifest.error_map.get(code_str)

        if mapped_code_name and hasattr(ErrorCode, mapped_code_name):
            error_code = ErrorCode[mapped_code_name]
        elif status_code == 429:
            error_code = ErrorCode.PLATFORM_RATE_LIMIT
        elif status_code in (401, 403):
            error_code = ErrorCode.CONNECTION_AUTH_EXPIRED
        elif status_code == 422:
            error_code = ErrorCode.PLATFORM_CONTENT_REJECTED
        elif status_code >= 500:
            error_code = ErrorCode.PLATFORM_UNAVAILABLE
        else:
            error_code = ErrorCode.INTERNAL_ERROR

        retry_after = None
        if headers:
            retry_header = headers.get("retry-after") or headers.get("Retry-After")
            if retry_header and str(retry_header).isdigit():
                retry_after = int(retry_header)

        details = {"platform_status_code": status_code, "platform_body": response_text}
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after

        msg = f"Platform returned HTTP {status_code}: {response_text or 'No details'}"
        if error_code == ErrorCode.PLATFORM_RATE_LIMIT:
            return PlatformRateLimitError(message=msg, retry_after=retry_after)
        if error_code == ErrorCode.CONNECTION_AUTH_EXPIRED:
            return ConnectionAuthExpiredError(message=msg)
        if error_code == ErrorCode.PLATFORM_CONTENT_REJECTED:
            return PlatformContentRejectedError(message=msg, platform_reason=response_text)
        if error_code == ErrorCode.PLATFORM_UNAVAILABLE:
            return PlatformUnavailableError(message=msg)

        return IncuBrixError(
            code=error_code,
            message=msg,
            details=details,
            status_code=status_code if 400 <= status_code < 500 else 502,
        )

