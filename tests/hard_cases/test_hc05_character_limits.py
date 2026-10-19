import pytest
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError
from engine.publisher import PublishEngine
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_hc05_character_limits_violation_pre_flight():
    """HC5: Title or body exceeds platform character limits.

    Expected: Pre-flight validation fails with DEST_SPEC_VIOLATION, listing
    field-level length violations; request never sent to platform.
    """
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest)
    publisher = PublishEngine()

    # Title exceeds 255 chars, body exceeds 50000 chars
    long_title = "A" * 300
    long_body = "B" * 55000

    rendition = Rendition(title=long_title, body=long_body)
    destination = DestinationPayload(
        id="dest_disc_hc5",
        name="Discourse Forum",
        platform_key="discourse",
        parameters={
            "base_url": "http://test/discourse",
            "title_max_chars": 255,
            "body_max_chars": 50000,
        },
    )
    connection = ConnectionPayload(base_url="http://test/discourse", api_key="k")

    # Spy: mock connector to verify it is NEVER called
    connector.publish = AsyncMock()

    with pytest.raises(IncuBrixError) as exc_info:
        await publisher.publish(
            rendition=rendition,
            destination=destination,
            connection=connection,
            idempotency_key="idemp_hc05",
            connector_override=connector,
        )

    err = exc_info.value
    assert err.code == ErrorCode.DEST_SPEC_VIOLATION
    assert err.status_code == 422
    assert "format_limits" in err.message or "Title exceeds" in err.message

    # SPY PROOF: connector publish method was NEVER called!
    assert connector.publish.call_count == 0
    print(f"\n[HC5 PASS] Character limit violation caught pre-flight. Spy proves connector was never invoked.")
