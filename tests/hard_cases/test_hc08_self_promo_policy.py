import pytest
from unittest.mock import AsyncMock
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError
from engine.publisher import PublishEngine


@pytest.mark.asyncio
async def test_hc08_self_promotion_policy_enforcement():
    """HC8: Promotional post submitted to community with self_promo_allowed: false.

    Expected: Rules engine rejects post with rule violation; marks required human
    review or blocks delivery entirely. Spy proves connector is never called.
    """
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest)
    publisher = PublishEngine()

    rendition = Rendition(
        title="Check out our special discount and buy now!",
        body="Limited time offer: get 50% discount on our SaaS subscription now.",
        custom_fields={"is_promotional": True},
    )
    destination = DestinationPayload(
        id="dest_disc_hc8",
        name="Strict Anti-Promo Community",
        platform_key="discourse",
        parameters={
            "base_url": "http://test/discourse",
            "self_promo_allowed": False,  # Strict ban on promotional content
        },
    )
    connection = ConnectionPayload(base_url="http://test/discourse", api_key="k")

    connector.publish = AsyncMock()

    with pytest.raises(IncuBrixError) as exc_info:
        await publisher.publish(
            rendition=rendition,
            destination=destination,
            connection=connection,
            idempotency_key="idemp_hc08",
            connector_override=connector,
        )

    err = exc_info.value
    assert err.code == ErrorCode.PLATFORM_CONTENT_REJECTED
    assert err.status_code == 422
    assert "self_promo" in err.message or "promotional" in err.message
    assert err.details.get("required_human_action") is not None

    # SPY PROOF: connector was never invoked
    assert connector.publish.call_count == 0
    print(f"\n[HC8 PASS] Promotional post rejected pre-flight. Spy proves connector was never invoked.")
