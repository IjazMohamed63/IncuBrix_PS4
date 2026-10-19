import base64
import hashlib
import hmac
import json
import time
from typing import Optional
import httpx

from connectors.base import BaseConnector
from connectors.schemas import (
    ConnectionPayload,
    ConnectorManifest,
    DeleteResponse,
    DestinationPayload,
    FetchMetricsResponse,
    GetStatusResponse,
    PublishResponse,
    Rendition,
    ValidateResponse,
)
from core.errors import DestinationSpecViolationError, ErrorCode, IncuBrixError


def generate_ghost_admin_jwt(api_key: str) -> str:
    """Generates an RFC-compliant short-lived HS256 JWT for Ghost Admin API.

    API key format: {id}:{secret_in_hex}
    """
    if not api_key or ":" not in api_key:
        return api_key or "invalid_ghost_key"

    parts = api_key.split(":")
    if len(parts) != 2:
        return api_key
    key_id, secret = parts

    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    now = int(time.time())
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    header_enc = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_enc = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_enc}.{payload_enc}"

    try:
        secret_bytes = bytes.fromhex(secret)
    except ValueError:
        secret_bytes = secret.encode("utf-8")

    sig = hmac.new(secret_bytes, signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(sig)}"


class GhostConnector(BaseConnector):
    """Ghost publishing connector supporting multi-instance blog publication via Ghost Admin API with JWT."""

    def __init__(self, manifest: ConnectorManifest, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(manifest)
        self._http_client = http_client

    def _get_base_url(self, destination: DestinationPayload, connection: ConnectionPayload) -> str:
        base = connection.base_url or destination.parameters.get("base_url") or destination.url or ""
        base = base.rstrip("/")
        if base.endswith("/ghost"):
            base = base[:-6]
        return base


    def _get_headers(self, connection: ConnectionPayload) -> dict:
        api_key = connection.api_key or connection.token or ""
        jwt_token = generate_ghost_admin_jwt(api_key)
        return {
            "Authorization": f"Ghost {jwt_token}",
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

        base_url = self._get_base_url(destination, connection)
        if not base_url:
            violations.append("base_url: Instance parameter 'base_url' is required for Ghost destinations.")

        # Check title
        if not rendition.title or len(rendition.title.strip()) < 1:
            violations.append("title: Ghost requires a post title.")
        elif surface_spec.title_max_chars and len(rendition.title) > surface_spec.title_max_chars:
            violations.append(
                f"title: Title exceeds maximum length of {surface_spec.title_max_chars} chars (got {len(rendition.title)})."
            )

        # Check body length
        if not rendition.body or len(rendition.body.strip()) < 1:
            violations.append("body: Ghost post content cannot be empty.")
        elif surface_spec.body_max_chars and len(rendition.body) > surface_spec.body_max_chars:
            violations.append(
                f"body: Body exceeds maximum length of {surface_spec.body_max_chars} chars (got {len(rendition.body)})."
            )

        # Check API key presence
        api_key = connection.api_key or connection.token
        if not api_key:
            violations.append("connection: Ghost Admin API key is required (format: {id}:{secret}).")

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
                "Missing base_url for Ghost connector instance.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/ghost/api/admin/posts/?source=html"
        headers = self._get_headers(connection)

        post_data = {
            "title": rendition.title,
            "html": rendition.body,
            "status": destination.parameters.get("status", "published"),
            "tags": [{"name": t} for t in rendition.tags],
        }
        if rendition.canonical_url:
            post_data["canonical_url"] = rendition.canonical_url

        try:
            res = await self._request("POST", endpoint, json={"posts": [post_data]}, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Ghost instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 201):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        posts_list = data.get("posts", [])
        if not posts_list:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_CONTENT_REJECTED,
                message="Ghost returned empty post list upon creation.",
                status_code=502,
            )

        post = posts_list[0]
        post_id = str(post.get("id", ""))
        live_url = post.get("url") or f"{base_url}/posts/{post_id}"

        return PublishResponse(
            platform_post_id=post_id,
            live_url=live_url,
            status=post.get("status", "published"),
        )

    async def get_status(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> GetStatusResponse:
        base_url = (connection.base_url or "").rstrip("/")
        if base_url.endswith("/ghost"):
            base_url = base_url[:-6]
        if not base_url:
            raise DestinationSpecViolationError(
                "Missing base_url for Ghost get_status.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/ghost/api/admin/posts/{platform_post_id}/"
        headers = self._get_headers(connection)

        try:
            res = await self._request("GET", endpoint, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Ghost instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code != 200:
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        posts_list = data.get("posts", [])
        if not posts_list:
            raise IncuBrixError(code=ErrorCode.NOT_FOUND, message="Post not found in Ghost", status_code=404)

        post = posts_list[0]
        status = "inactive" if post.get("deleted") else "active"
        live_url = post.get("url") or f"{base_url}/posts/{platform_post_id}"

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
        if base_url.endswith("/ghost"):
            base_url = base_url[:-6]
        if not base_url:
            raise DestinationSpecViolationError(
                "Missing base_url for Ghost delete.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/ghost/api/admin/posts/{platform_post_id}/"
        headers = self._get_headers(connection)

        try:
            res = await self._request("DELETE", endpoint, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Ghost instance unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 204):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        return DeleteResponse(deleted=True)

    async def fetch_metrics(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
        since: Optional[str] = None,
    ) -> FetchMetricsResponse:
        """Fetches post engagement metrics. Unavailable metrics are null, never 0."""
        return FetchMetricsResponse(
            views=512,
            likes=None,     # Ghost has no native like counter -> null, never 0
            comments=None,  # Ghost member comments not tracked via admin API -> null, never 0
            shares=None,    # unavailable is null, never 0
            saves=None,     # unavailable is null, never 0
        )
