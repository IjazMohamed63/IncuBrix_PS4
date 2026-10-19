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


class DiscourseConnector(BaseConnector):
    """Discourse forum connector supporting multi-instance operations via base_url."""

    def __init__(self, manifest: ConnectorManifest, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(manifest)
        self._http_client = http_client

    def _get_base_url(self, destination: DestinationPayload, connection: ConnectionPayload) -> str:
        base = connection.base_url or destination.parameters.get("base_url") or destination.url or ""
        return base.rstrip("/")

    def _get_headers(self, connection: ConnectionPayload) -> dict:
        api_key = connection.api_key or ""
        username = connection.extra.get("username") or connection.client_id or "system"
        return {
            "Api-Key": api_key,
            "Api-Username": username,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if self._http_client:
            return await self._http_client.request(method, url, **kwargs)
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await client.request(method, url, **kwargs)

    async def validate(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
    ) -> ValidateResponse:
        violations = []
        surface_spec = self.manifest.surfaces[0].spec

        base_url = self._get_base_url(destination, connection)
        if not base_url:
            violations.append("base_url: Instance parameter 'base_url' is required for Discourse destinations.")

        # Check title length
        if not rendition.title or len(rendition.title.strip()) < 5:
            violations.append("title: Discourse requires a title of at least 5 characters.")
        elif surface_spec.title_max_chars and len(rendition.title) > surface_spec.title_max_chars:
            violations.append(
                f"title: Title exceeds maximum length of {surface_spec.title_max_chars} chars (got {len(rendition.title)})."
            )

        # Check body length
        if not rendition.body or len(rendition.body.strip()) < 10:
            violations.append("body: Discourse post body must be at least 10 characters.")
        elif surface_spec.body_max_chars and len(rendition.body) > surface_spec.body_max_chars:
            violations.append(
                f"body: Body exceeds maximum length of {surface_spec.body_max_chars} chars (got {len(rendition.body)})."
            )

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
        if not base_url:
            raise DestinationSpecViolationError(
                "Missing base_url for Discourse connector instance.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/posts.json"
        headers = self._get_headers(connection)

        post_body = {
            "title": rendition.title,
            "raw": rendition.body,
        }
        if "category_id" in destination.parameters:
            post_body["category"] = destination.parameters["category_id"]
        elif "category" in destination.parameters:
            post_body["category"] = destination.parameters["category"]

        if "topic_id" in destination.parameters:
            post_body["topic_id"] = destination.parameters["topic_id"]

        try:
            res = await self._request("POST", endpoint, json=post_body, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Discourse instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 201):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        post_id = str(data.get("id") or data.get("discourse_post_identifier", ""))
        topic_id = data.get("topic_id", post_id)
        post_number = data.get("post_number", 1)
        live_url = f"{base_url}/t/{topic_id}/{post_number}"

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
        base_url = (connection.base_url or "").rstrip("/")
        if not base_url:
            raise DestinationSpecViolationError(
                "Missing base_url for Discourse get_status.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/posts/{platform_post_id}.json"
        headers = self._get_headers(connection)

        try:
            res = await self._request("GET", endpoint, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Discourse instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code != 200:
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        if data.get("deleted") or data.get("hidden"):
            status = "inactive"
        else:
            status = "active"

        topic_id = data.get("topic_id", platform_post_id)
        post_number = data.get("post_number", 1)
        live_url = f"{base_url}/t/{topic_id}/{post_number}"

        return GetStatusResponse(
            status=status,
            live_url=live_url,
        )

    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> DeleteResponse:
        base_url = (connection.base_url or "").rstrip("/")
        if not base_url:
            raise DestinationSpecViolationError(
                "Missing base_url for Discourse delete.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/posts/{platform_post_id}.json"
        headers = self._get_headers(connection)

        try:
            res = await self._request("DELETE", endpoint, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Discourse instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 204):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        return DeleteResponse(deleted=True)
