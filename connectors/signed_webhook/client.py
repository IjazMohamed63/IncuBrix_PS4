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
    GetStatusResponse,
    PublishResponse,
    Rendition,
    ValidateResponse,
)
from core.errors import DestinationSpecViolationError, ErrorCode, IncuBrixError
from core.logging import get_logger

logger = get_logger("signed_webhook")


class SignedWebhookConnector(BaseConnector):
    """Secure signed webhook delivery connector using HMAC-SHA256 and replay protection."""

    def __init__(self, manifest: ConnectorManifest, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(manifest)
        self._http_client = http_client

    def _get_target_url(self, destination: DestinationPayload, connection: ConnectionPayload) -> str:
        url = connection.base_url or destination.parameters.get("base_url") or destination.url or ""
        return url.rstrip("/")

    def _get_secret(self, connection: ConnectionPayload) -> str:
        # Note: secret is strictly kept in memory and never logged
        return connection.api_key or connection.client_secret or "test_webhook_secret_key_12345"

    def _sign_payload(self, body_str: str, secret: str, timestamp: int) -> str:
        payload_to_sign = f"{timestamp}.{body_str}"
        return hmac.new(secret.encode("utf-8"), payload_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

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

        target_url = self._get_target_url(destination, connection)
        if not target_url or not (target_url.startswith("http://") or target_url.startswith("https://")):
            violations.append("url: Destination must specify a valid HTTP or HTTPS webhook target URL.")

        # Check body length
        body_bytes = len(rendition.body.encode("utf-8"))
        if surface_spec.body_max_chars and body_bytes > surface_spec.body_max_chars:
            violations.append(
                f"body: Webhook payload exceeds maximum limit of {surface_spec.body_max_chars} bytes (got {body_bytes})."
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

        target_url = self._get_target_url(destination, connection)
        if not target_url:
            raise DestinationSpecViolationError(
                "Missing target webhook URL.",
                ["destination.url"],
            )

        # Prepare payload dictionary
        now = int(time.time())
        payload_dict = {
            "idempotency_key": idempotency_key,
            "event": "distribution.publish",
            "timestamp": now,
            "rendition": rendition.model_dump(),
            "destination": destination.model_dump(),
        }
        body_str = json.dumps(payload_dict, separators=(",", ":"))

        # Compute HMAC signature with secret - NEVER LOG SECRET
        secret = self._get_secret(connection)
        signature = self._sign_payload(body_str, secret, now)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-IncuBrix-Signature": f"t={now},v1={signature}",
            "X-IncuBrix-Timestamp": str(now),
        }

        # Safe logging: log target and timestamp only, never the signing secret or token
        logger.info(f"Dispatching signed webhook to {target_url} with timestamp {now}")

        endpoint = target_url if target_url.endswith("/partner/webhook") else f"{target_url}/partner/webhook"
        try:
            res = await self._request("POST", endpoint, content=body_str.encode("utf-8"), headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Webhook target unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 201, 202):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        delivery_id = str(data.get("delivery_id", f"wh_{now}"))
        live_url = data.get("live_url") or f"{target_url}/deliveries/{delivery_id}"

        return PublishResponse(
            platform_post_id=delivery_id,
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
                "Missing base_url for webhook delivery get_status.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/partner/webhook/deliveries/{platform_post_id}"
        headers = {"Accept": "application/json"}

        try:
            res = await self._request("GET", endpoint, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Webhook partner service unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code != 200:
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        data = res.json()
        status = "inactive" if data.get("deleted") else "active"
        live_url = data.get("live_url") or f"{base_url}/deliveries/{platform_post_id}"

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
                "Missing base_url for webhook delivery delete.",
                ["connection.base_url"],
            )

        endpoint = f"{base_url}/partner/webhook/deliveries/{platform_post_id}"
        headers = {"Accept": "application/json"}

        try:
            res = await self._request("DELETE", endpoint, headers=headers)
        except httpx.RequestError as exc:
            raise IncuBrixError(
                code=ErrorCode.PLATFORM_UNAVAILABLE,
                message=f"Webhook partner service unreachable at {endpoint}: {str(exc)}",
                retryable=True,
                status_code=503,
            )

        if res.status_code not in (200, 204):
            raise self.map_http_status_to_error(res.status_code, res.text, headers=dict(res.headers))

        return DeleteResponse(deleted=True)
