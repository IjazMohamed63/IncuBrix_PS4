import pytest
from httpx import AsyncClient, ASGITransport
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError
from mock_platforms.main import app as mock_platforms_app, scenarios


@pytest.fixture
def mock_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_hc04_content_rejected_by_platform_moderation(mock_client):
    """HC4: Content rejected by platform rules/moderation (HTTP 422).

    Expected: Map to PLATFORM_CONTENT_REJECTED, extract platform rejection message,
    fail job with non-retryable error, preserve log.
    """
    scenarios.clear()
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest, http_client=mock_client)

    rendition = Rendition(title="Questionable Title", body="Content that triggers community moderation filters.")
    destination = DestinationPayload(
        id="dest_disc_hc4",
        name="Moderated Community",
        parameters={"base_url": "http://test/discourse"},
    )
    connection = ConnectionPayload(
        base_url="http://test/discourse",
        api_key="valid_key",
    )

    # Script 422 Unprocessable Entity
    rejection_reason = "Post contains blacklisted keywords rejected by community moderation bot."
    scenarios["discourse"] = {"status_code": 422, "error_message": rejection_reason}

    with pytest.raises(IncuBrixError) as exc_info:
        await connector.publish(rendition, destination, connection, "idemp_hc04")

    err = exc_info.value
    assert err.code == ErrorCode.PLATFORM_CONTENT_REJECTED
    assert err.retryable is False
    assert err.status_code == 422
    assert rejection_reason in err.message or rejection_reason in str(err.details)
    print(f"\n[HC4 PASS] HTTP 422 mapped to non-retryable PLATFORM_CONTENT_REJECTED with platform details preserved.")
