import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, PublishResponse, Rendition
from core.errors import ErrorCode, IncuBrixError
from engine.publisher import PublishEngine
from engine.rules_engine import audit_store


@pytest.mark.asyncio
async def test_hc07_frequency_cap_enforcement_and_reschedule():
    """HC7: Second post submitted within destination's frequency cap window.

    Expected: Pre-flight rules engine blocks immediate post with
    DEST_RULE_FREQUENCY_CAP, calculating exact reschedule_at timestamp.
    Spy proves second post never reaches the connector.
    """
    audit_store.clear()
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest)
    publisher = PublishEngine()

    dest_id = "dest_disc_hc7"
    destination = DestinationPayload(
        id=dest_id,
        name="High Frequency Forum",
        platform_key="discourse",
        parameters={
            "base_url": "http://test/discourse",
            "frequency_cap": 24,  # 24 hours required between posts
        },
    )
    connection = ConnectionPayload(base_url="http://test/discourse", api_key="k")
    rendition = Rendition(title="First Post", body="First post content.")

    # Mock connector.publish to succeed for the first call
    connector.publish = AsyncMock(
        return_value=PublishResponse(
            platform_post_id="post_hc7_1",
            live_url="http://test/discourse/t/100/1",
            status="published",
        )
    )

    # 1. First publish succeeds and updates publication history
    first_res = await publisher.publish(
        rendition=rendition,
        destination=destination,
        connection=connection,
        idempotency_key="idemp_hc7_first",
        connector_override=connector,
    )
    assert first_res["status"] == "published"
    assert connector.publish.call_count == 1

    # 2. Reset connector spy call count
    connector.publish.reset_mock()

    # 3. Second publish submitted immediately within the 24h window
    rendition_2 = Rendition(title="Second Post Too Soon", body="Attempting to post too quickly.")

    with pytest.raises(IncuBrixError) as exc_info:
        await publisher.publish(
            rendition=rendition_2,
            destination=destination,
            connection=connection,
            idempotency_key="idemp_hc7_second",
            connector_override=connector,
        )

    err = exc_info.value
    assert err.code == ErrorCode.DEST_RULE_FREQUENCY_CAP
    assert err.status_code == 429
    assert err.retryable is True
    assert "retry_at" in err.details
    assert err.details["retry_at"] is not None

    # SPY PROOF: Second post NEVER reached connector!
    assert connector.publish.call_count == 0
    print(f"\n[HC7 PASS] Frequency cap enforced: second post blocked with next_allowed_at={err.details['retry_at']}.")
    print("           Spy verifies connector call count for second post is strictly 0.")
