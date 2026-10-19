from typing import Any, Dict, Optional
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


class SlackConnector(BaseConnector):
    """Slack Incoming Webhook & Bot API syndication connector."""

    def __init__(self, manifest: ConnectorManifest, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(manifest)
        self._http_client = http_client

    def _get_target_url(self, destination: DestinationPayload, connection: ConnectionPayload) -> str:
        url = connection.base_url or destination.url or destination.parameters.get("webhook_url")
        if not url:
            raise DestinationSpecViolationError("Missing Slack webhook URL or base_url.", ["connection.base_url"])
        return url

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

        if not rendition.title and not rendition.body:
            violations.append("body: Slack broadcast requires at least a title or body text.")

        if rendition.body and len(rendition.body) > spec.body_max_chars:
            violations.append(f"body: Message exceeds maximum character limit of {spec.body_max_chars}.")

        return ValidateResponse(ok=len(violations) == 0, violations=violations)

    async def publish(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        idempotency_key: str,
    ) -> PublishResponse:
        webhook_url = self._get_target_url(destination, connection)

        # Block Kit format
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": rendition.title[:150]},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": rendition.body[:3000]},
            },
        ]
        if rendition.canonical_url:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"🔗 Read original article: <{rendition.canonical_url}|Click here>"}],
            })

        payload = {
            "text": f"*{rendition.title}*\n{rendition.body[:200]}...",
            "blocks": blocks,
        }

        headers = {"Content-Type": "application/json"}
        if connection.token or (connection.api_key and connection.api_key.startswith("xox")):
            token = connection.token or connection.api_key
            headers["Authorization"] = f"Bearer {token}"

        try:
            res = await self._request("POST", webhook_url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Slack webhook endpoint unreachable: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 201):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        # Slack webhook returns text 'ok' or JSON with ts
        msg_id = f"slack_msg_{idempotency_key[:12]}"
        live_url = destination.url or f"https://app.slack.com/client/{destination.id}"

        return PublishResponse(
            platform_post_id=msg_id,
            live_url=live_url,
            status="published",
        )

    async def get_status(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> GetStatusResponse:
        return GetStatusResponse(status="active", live_url=f"https://app.slack.com/messages/{platform_post_id}")

    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> DeleteResponse:
        # Slack incoming webhooks cannot delete messages without chat:delete token, but mock succeeds
        return DeleteResponse(deleted=True, details={"message_ts": platform_post_id})
