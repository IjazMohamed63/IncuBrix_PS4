from typing import Optional
import httpx

from connectors.base import BaseConnector
from connectors.schemas import (
    ConnectionPayload,
    ConnectorManifest,
    DeleteResponse,
    DestinationPayload,
    GetStatusResponse,
    PublishResponse,
    Rendition,
    ValidateResponse,
)
from core.errors import DestinationSpecViolationError, ErrorCode, IncuBrixError


class DevtoConnector(BaseConnector):
    """Dev.to / Forem API publishing connector with mock/sandbox support."""

    def __init__(self, manifest: ConnectorManifest, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(manifest)
        self._http_client = http_client

    def _get_base_url(self, destination: DestinationPayload, connection: ConnectionPayload) -> str:
        base = connection.base_url or destination.parameters.get("base_url") or destination.url or "https://dev.to"
        return base.rstrip("/")

    def _get_headers(self, connection: ConnectionPayload) -> dict:
        api_key = connection.api_key or ""
        return {
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        return await self.execute_request(self._http_client, method, url, **kwargs)

    async def validate(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
    ) -> ValidateResponse:
        violations = []
        surface_spec = self.manifest.surfaces[0].spec

        # Check title
        if not rendition.title or len(rendition.title.strip()) < 5:
            violations.append("title: Dev.to requires an article title of at least 5 characters.")
        elif surface_spec.title_max_chars and len(rendition.title) > surface_spec.title_max_chars:
            violations.append(
                f"title: Title exceeds maximum length of {surface_spec.title_max_chars} chars (got {len(rendition.title)})."
            )

        # Check body length
        if not rendition.body or len(rendition.body.strip()) < 20:
            violations.append("body: Dev.to article body must contain at least 20 characters of markdown.")
        elif surface_spec.body_max_chars and len(rendition.body) > surface_spec.body_max_chars:
            violations.append(
                f"body: Body exceeds maximum length of {surface_spec.body_max_chars} chars (got {len(rendition.body)})."
            )

        # Check tags limit (Dev.to max 4 tags)
        if len(rendition.tags) > 4:
            violations.append(f"tags: Dev.to allows a maximum of 4 tags (got {len(rendition.tags)}).")

        # Allow simulated validation failures
        if rendition.custom_fields.get("simulate_violation"):
            violations.append(str(rendition.custom_fields["simulate_violation"]))

        return ValidateResponse(ok=(len(violations) == 0), violations=violations)

    async def publish(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        idempotency_key: str,
    ) -> PublishResponse:
        # Check for simulated errors
        sim_status = rendition.custom_fields.get("simulate_http_status")
        if sim_status:
            headers = {"Retry-After": "30"} if int(sim_status) == 429 else None
            raise self.map_http_status_to_error(int(sim_status), "Simulated platform error", headers=headers)

        base_url = self._get_base_url(destination, connection)
        endpoint = f"{base_url}/api/articles"
        headers = self._get_headers(connection)

        article_payload = {
            "title": rendition.title,
            "body_markdown": rendition.body,
            "published": True,
            "tags": rendition.tags[:4],
        }
        if rendition.canonical_url:
            article_payload["canonical_url"] = rendition.canonical_url

        try:
            res = await self._request("POST", endpoint, json={"article": article_payload}, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Dev.to API unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 201):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        post_id = str(data.get("id", ""))
        live_url = data.get("url") or f"{base_url}/articles/{post_id}"

        return PublishResponse(
            platform_post_id=post_id,
            live_url=live_url,
            status="published",
        )

    async def get_status(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> GetStatusResponse:
        base_url = (connection.base_url or "https://dev.to").rstrip("/")
        endpoint = f"{base_url}/api/articles/{platform_post_id}"
        headers = self._get_headers(connection)

        try:
            res = await self._request("GET", endpoint, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Dev.to API unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code != 200:
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        live_url = data.get("url") or f"{base_url}/articles/{platform_post_id}"
        status = "inactive" if data.get("deleted") else "active"

        return GetStatusResponse(
            status=status,
            live_url=live_url,
        )

    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> DeleteResponse:
        base_url = (connection.base_url or "https://dev.to").rstrip("/")
        endpoint = f"{base_url}/api/articles/{platform_post_id}"
        headers = self._get_headers(connection)

        try:
            res = await self._request("DELETE", endpoint, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Dev.to API unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 204):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        return DeleteResponse(deleted=True)
