import pytest
from httpx import AsyncClient, ASGITransport
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError, PlatformRateLimitError
from core.rate_limiter import rate_limiter
from engine.publisher import PublishEngine
from mock_platforms.main import app as mock_platforms_app, scenarios


@pytest.fixture
def mock_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_hc02_platform_rate_limit_and_backoff_window(mock_client):
    """HC2: Platform returns HTTP 429 with Retry-After / reset timestamp.

    Expected: Map to PLATFORM_RATE_LIMIT, extract reset epoch, persist backoff
    window, reject subsequent requests until window elapses.
    """
    scenarios.clear()
    await rate_limiter.reset()

    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest, http_client=mock_client)
    publisher = PublishEngine()

    rendition = Rendition(
        title="Valid Discussion Topic for Rate Limit Testing",
        body="Detailed discussion on backoff strategies and token buckets.",
    )
    destination = DestinationPayload(
        id="dest_disc_hc2",
        name="Forum Rate Limit Target",
        platform_key="discourse",
        parameters={"base_url": "http://test/discourse"},
    )
    connection = ConnectionPayload(
        base_url="http://test/discourse",
        api_key="valid_key",
    )

    # Step 1: Script platform to return 429 with Retry-After: 45
    scenarios["discourse"] = {"status_code": 429, "retry_after": 45}

    # Step 2: First publish request fails with 429 and extracts reset time
    with pytest.raises(PlatformRateLimitError) as exc_info:
        await publisher.publish(
            rendition=rendition,
            destination=destination,
            connection=connection,
            idempotency_key="idemp_hc02_first_call",
            connector_override=connector,
        )

    err = exc_info.value
    assert err.code == ErrorCode.PLATFORM_RATE_LIMIT
    assert err.retryable is True
    assert err.details.get("retry_after_seconds") == 45

    # Step 3: Clear mock scenario so platform would return 200 now
    scenarios.clear()

    # Step 4: Immediately attempt second publish to the same destination.
    # Expected: The rate_limiter has persisted the backoff window and BLOCKS the call immediately!
    with pytest.raises(PlatformRateLimitError) as second_exc:
        await publisher.publish(
            rendition=rendition,
            destination=destination,
            connection=connection,
            idempotency_key="idemp_hc02_second_call",
            connector_override=connector,
        )

    second_err = second_exc.value
    assert second_err.code == ErrorCode.PLATFORM_RATE_LIMIT
    assert "backoff active" in second_err.message.lower()
    print(f"\n[HC2 PASS] 429 backoff window verified: subsequent call rejected prior to network dispatch.")
