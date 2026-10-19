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


class LemmyConnector(BaseConnector):
    """Lemmy federated community connector supporting multi-instance operations via base_url."""

    def __init__(self, manifest: ConnectorManifest, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(manifest)
        self._http_client = http_client

    def _get_base_url(self, destination: DestinationPayload, connection: ConnectionPayload) -> str:
        base = connection.base_url or destination.parameters.get("base_url") or destination.url or ""
        return base.rstrip("/")

    def _get_token(self, connection: ConnectionPayload) -> str:
        return connection.token or connection.api_key or ""

    def _get_headers(self, connection: ConnectionPayload) -> dict:
        token = self._get_token(connection)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

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
            violations.append("base_url: Instance parameter 'base_url' is required for Lemmy destinations.")

        # Check title length (Lemmy name max 100)
        if not rendition.title or len(rendition.title.strip()) < 3:
            violations.append("title: Lemmy requires a post title of at least 3 characters.")
        elif surface_spec.title_max_chars and len(rendition.title) > surface_spec.title_max_chars:
            violations.append(
                f"title: Title exceeds maximum length of {surface_spec.title_max_chars} chars (got {len(rendition.title)})."
            )

        # Check body length
        if surface_spec.body_max_chars and len(rendition.body) > surface_spec.body_max_chars:
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
                "Missing base_url for Lemmy connector instance.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/api/v3/post"
        headers = self._get_headers(connection)
        token = self._get_token(connection)

        community_id = destination.parameters.get("community_id", 1)
        post_body = {
            "name": rendition.title,
            "body": rendition.body,
            "community_id": community_id,
            "auth": token,
        }
        if rendition.canonical_url:
            post_body["url"] = rendition.canonical_url

        try:
            res = await self._request("POST", endpoint, json=post_body, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Lemmy instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 201):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        post_view = data.get("post_view", {})
        post_obj = post_view.get("post", data)
        post_id = str(post_obj.get("id", ""))
        live_url = f"{base_url}/post/{post_id}"

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
                "Missing base_url for Lemmy get_status.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/api/v3/post"
        headers = self._get_headers(connection)
        params = {"id": platform_post_id}

        try:
            res = await self._request("GET", endpoint, params=params, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Lemmy instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code != 200:
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        post_view = data.get("post_view", {})
        post_obj = post_view.get("post", data)

        is_deleted = post_obj.get("deleted", False) or post_obj.get("removed", False)
        status = "inactive" if is_deleted else "active"
        live_url = f"{base_url}/post/{platform_post_id}"

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
                "Missing base_url for Lemmy delete.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/api/v3/post/delete"
        headers = self._get_headers(connection)
        token = self._get_token(connection)

        delete_body = {
            "post_id": int(platform_post_id) if platform_post_id.isdigit() else platform_post_id,
            "deleted": True,
            "auth": token,
        }

        try:
            res = await self._request("POST", endpoint, json=delete_body, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Lemmy instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 204):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        return DeleteResponse(deleted=True)
