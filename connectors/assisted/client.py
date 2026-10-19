from connectors.base import BaseConnector
from connectors.schemas import (
    BuildAssistPackResponse,
    ChecklistItem,
    ConnectionPayload,
    ConnectorManifest,
    DeleteResponse,
    DestinationPayload,
    GetStatusResponse,
    PublishResponse,
    Rendition,
    ValidateResponse,
)
from core.errors import ErrorCode, IncuBrixError


class AssistedConnector(BaseConnector):
    """Assisted posting connector for high-trust communities where automated publishing is banned.

    Builds an assist pack for manual human delivery. Package creation is never reported as 'published'.
    """

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

        # Check title
        if not rendition.title or len(rendition.title.strip()) < 1:
            violations.append("title: Assisted pack requires a post title.")
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
        """Automated publishing is strictly disallowed on assisted destinations."""
        raise IncuBrixError(
            code=ErrorCode.DEST_SPEC_VIOLATION,
            message="Assisted connector does not support automated publishing. Use build_assist_pack instead. Package creation is never reported as 'published'.",
            retryable=False,
            status_code=422,
        )

    async def get_status(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> GetStatusResponse:
        raise IncuBrixError(
            code=ErrorCode.DEST_SPEC_VIOLATION,
            message="Assisted connector does not support automated get_status.",
            retryable=False,
            status_code=400,
        )

    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> DeleteResponse:
        raise IncuBrixError(
            code=ErrorCode.DEST_SPEC_VIOLATION,
            message="Assisted connector does not support automated delete.",
            retryable=False,
            status_code=400,
        )

    async def build_assist_pack(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
    ) -> BuildAssistPackResponse:
        # 1. Collect media files
        files = [m.url for m in rendition.media]

        # 2. Build human-ready caption
        caption = f"{rendition.title}\n\n{rendition.body}"
        if rendition.ai_disclosure:
            caption += f"\n\n[AI Disclosure: {rendition.ai_disclosure}]"

        # 3. Form deep link
        deep_link = destination.url or destination.parameters.get("submit_url") or "https://community.local/submit"

        # 4. Form comprehensive pre-posting checklist
        checklist = [
            ChecklistItem(
                id="chk_manual_post",
                label="Confirm manual posting: Automated bot activity is strictly forbidden in this community.",
                required=True,
            ),
            ChecklistItem(
                id="chk_self_promo",
                label="Verify community self-promotion rules (ensure compliant ratio with non-promotional activity).",
                required=True,
            ),
            ChecklistItem(
                id="chk_flair",
                label="Select the appropriate post flair/category on the submission page.",
                required=True,
            ),
        ]
        if rendition.ai_disclosure:
            checklist.append(
                ChecklistItem(
                    id="chk_ai_disclosure",
                    label=f"Confirm AI disclosure text is visible: '{rendition.ai_disclosure}'",
                    required=True,
                )
            )

        return BuildAssistPackResponse(
            files=files,
            caption=caption,
            deep_link=deep_link,
            checklist=checklist,
        )
