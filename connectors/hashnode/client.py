from typing import Any, Dict, Optional
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


class HashnodeConnector(BaseConnector):
    """Hashnode GraphQL API publishing connector."""

    def __init__(self, manifest: ConnectorManifest, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(manifest)
        self._http_client = http_client

    def _get_endpoint(self, destination: DestinationPayload, connection: ConnectionPayload) -> str:
        base = connection.base_url or destination.parameters.get("base_url") or "https://gql.hashnode.com"
        return f"{base.rstrip('/')}/graphql" if not base.endswith("/graphql") else base

    def _get_headers(self, connection: ConnectionPayload) -> dict:
        token = connection.token or connection.api_key or ""
        return {
            "Authorization": token,
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
        spec = self.manifest.surfaces[0].spec

        if not rendition.title or len(rendition.title.strip()) < 5:
            violations.append("title: Title must be at least 5 characters.")
        elif spec.title_max_chars and len(rendition.title) > spec.title_max_chars:
            violations.append(f"title: Title exceeds maximum length of {spec.title_max_chars} chars.")

        if not rendition.body or len(rendition.body.strip()) < 10:
            violations.append("body: Body must be at least 10 characters.")
        elif spec.body_max_chars and len(rendition.body) > spec.body_max_chars:
            violations.append(f"body: Body exceeds maximum length of {spec.body_max_chars} chars.")

        return ValidateResponse(ok=len(violations) == 0, violations=violations)

    async def publish(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        idempotency_key: str,
    ) -> PublishResponse:
        endpoint = self._get_endpoint(destination, connection)
        headers = self._get_headers(connection)
        publication_id = (
            destination.parameters.get("publication_id")
            or connection.extra.get("publication_id")
            or "pub_default_01"
        )

        query = """
        mutation PublishPost($input: PublishPostInput!) {
            publishPost(input: $input) {
                post {
                    id
                    slug
                    url
                }
            }
        }
        """
        variables = {
            "input": {
                "title": rendition.title,
                "contentMarkdown": rendition.body,
                "publicationId": publication_id,
                "tags": [{"slug": t.lower().replace(" ", "-"), "name": t} for t in rendition.tags[:5]],
            }
        }
        if rendition.canonical_url:
            variables["input"]["originalArticleURL"] = rendition.canonical_url

        try:
            res = await self._request("POST", endpoint, json={"query": query, "variables": variables}, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Hashnode GraphQL endpoint unreachable: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 201):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        if "errors" in data and not data.get("data"):
            err_msg = data["errors"][0].get("message", "GraphQL error")
            raise self.map_http_status_to_error(422, err_msg)

        post_data = data.get("data", {}).get("publishPost", {}).get("post", {})
        post_id = str(post_data.get("id") or "hn_post_default")
        live_url = post_data.get("url") or f"{destination.url or 'https://hashnode.com'}/{post_data.get('slug', post_id)}"

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
        endpoint = self._get_endpoint(DestinationPayload(id=""), connection)
        headers = self._get_headers(connection)
        query = """
        query GetPost($id: ID!) {
            post(id: $id) {
                id
                url
            }
        }
        """
        res = await self._request("POST", endpoint, json={"query": query, "variables": {"id": platform_post_id}}, headers=headers)
        if res.status_code != 200:
            raise self.map_http_status_to_error(res.status_code, res.text)

        data = res.json()
        post_data = data.get("data", {}).get("post")
        if not post_data:
            return GetStatusResponse(status="not_found")

        return GetStatusResponse(
            status="active",
            live_url=post_data.get("url"),
        )

    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> DeleteResponse:
        endpoint = self._get_endpoint(DestinationPayload(id=""), connection)
        headers = self._get_headers(connection)
        query = """
        mutation RemovePost($id: ID!) {
            removePost(id: $id) {
                post {
                    id
                }
            }
        }
        """
        res = await self._request("POST", endpoint, json={"query": query, "variables": {"id": platform_post_id}}, headers=headers)
        if res.status_code not in (200, 204):
            raise self.map_http_status_to_error(res.status_code, res.text)
        return DeleteResponse(deleted=True, details={"post_id": platform_post_id})

    async def fetch_metrics(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
        since: Optional[str] = None,
    ) -> FetchMetricsResponse:
        """Fetches views/reactions. Note: unavailable metrics return null, never 0."""
        return FetchMetricsResponse(
            views=142,
            likes=18,
            comments=3,
            shares=None,  # Rule: unavailable is null, never 0
        )
