import pytest
from unittest.mock import AsyncMock
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, MediaItem, Rendition
from core.errors import ErrorCode, IncuBrixError
from engine.publisher import PublishEngine


@pytest.mark.asyncio
async def test_hc06_unsupported_media_format():
    """HC6: Media attachment format or file size unsupported by destination.

    Expected: Pre-flight validation fails with DEST_SPEC_VIOLATION detailing
    unsupported MIME type or exceeding size limit. Connector never called.
    """
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest)
    publisher = PublishEngine()

    rendition = Rendition(
        title="Valid Title With Video Attachment",
        body="Detailed discussion accompanied by a video file.",
        media=[
            MediaItem(
                url="https://media.local/video_demo.mp4",
                media_type="video/mp4",
                size_bytes=50000000,
            )
        ],
    )
    # Destination only allows images
    destination = DestinationPayload(
        id="dest_disc_hc6",
        name="Image-Only Forum",
        platform_key="discourse",
        parameters={
            "base_url": "http://test/discourse",
            "allowed_media_types": ["image/png", "image/jpeg"],
        },
    )
    connection = ConnectionPayload(base_url="http://test/discourse", api_key="k")

    connector.publish = AsyncMock()

    with pytest.raises(IncuBrixError) as exc_info:
        await publisher.publish(
            rendition=rendition,
            destination=destination,
            connection=connection,
            idempotency_key="idemp_hc06",
            connector_override=connector,
        )

    err = exc_info.value
    assert err.code == ErrorCode.DEST_SPEC_VIOLATION
    assert "video/mp4" in err.message or "content_type" in err.message
    # SPY PROOF: connector was never invoked
    assert connector.publish.call_count == 0
    print(f"\n[HC6 PASS] Unsupported media type blocked pre-flight. Spy proves connector was never invoked.")
