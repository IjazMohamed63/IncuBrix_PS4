from typing import Optional
from connectors.base import BaseConnector
from connectors.schemas import (
    BuildAssistPackResponse,
    ChecklistItem,
    ConnectionPayload,
    ConnectorManifest,
    DeleteResponse,
    DestinationPayload,
    FetchMetricsResponse,
    GetStatusResponse,
    PublishResponse,
    RefreshAuthResponse,
    Rendition,
    ValidateResponse,
)
from core.errors import ErrorCode, IncuBrixError


class StubConnector(BaseConnector):
    """Stub connector implementation for contract verification and pipeline tests."""

    def __init__(self, manifest: ConnectorManifest):
        super().__init__(manifest)

    async def validate(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
    ) -> ValidateResponse:
        violations = []
        surface_spec = self.manifest.surfaces[0].spec

        if surface_spec.title_max_chars and len(rendition.title) > surface_spec.title_max_chars:
            violations.append(
                f"Title exceeds maximum length of {surface_spec.title_max_chars} chars (got {len(rendition.title)})"
            )

        if surface_spec.body_max_chars and len(rendition.body) > surface_spec.body_max_chars:
            violations.append(
                f"Body exceeds maximum length of {surface_spec.body_max_chars} chars (got {len(rendition.body)})"
            )

        # Allow simulated validation failures via rendition.custom_fields
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
            raise self.map_http_status_to_error(int(sim_status), "Simulated platform error")

        post_id = f"stub_post_{idempotency_key[:8]}"
        base = connection.base_url or "http://stub.local"
        live_url = f"{base}/posts/{post_id}"

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
        base = connection.base_url or "http://stub.local"
        return GetStatusResponse(
            status="active",
            live_url=f"{base}/posts/{platform_post_id}",
        )

    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> DeleteResponse:
        if connection.extra.get("simulate_delete_fail"):
            return DeleteResponse(deleted=False)
        return DeleteResponse(deleted=True)

    async def fetch_metrics(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
        since: Optional[str] = None,
    ) -> FetchMetricsResponse:
        return FetchMetricsResponse(
            views=1250,
            likes=45,
            comments=12,
            shares=8,
            saves=19,
            watch_time_s=3600,
            clicks=110,
        )

    async def refresh_auth(
        self,
        connection: ConnectionPayload,
    ) -> RefreshAuthResponse:
        return RefreshAuthResponse(expires_at="2026-12-31T23:59:59Z")

    async def build_assist_pack(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
    ) -> BuildAssistPackResponse:
        return BuildAssistPackResponse(
            files=[m.url for m in rendition.media],
            caption=f"{rendition.title}\n\n{rendition.body[:280]}",
            deep_link=destination.url or "http://stub.local/submit",
            checklist=[
                ChecklistItem(id="chk_flair", label="Select 'Showcase' post flair", required=True),
                ChecklistItem(id="chk_guidelines", label="Confirm adherence to self-promo rules", required=True),
            ],
        )
