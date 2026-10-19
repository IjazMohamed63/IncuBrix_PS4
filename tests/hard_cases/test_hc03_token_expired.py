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
async def test_hc03_authentication_token_expired_or_revoked(mock_client):
    """HC3: Authentication token expired or revoked (HTTP 401).

    Expected: Map to CONNECTION_AUTH_EXPIRED, mark connection status degraded,
    pause destination, non-retryable error.
    """
    scenarios.clear()
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest, http_client=mock_client)

    rendition = Rendition(title="Valid Title", body="Valid discussion body content.")
    destination = DestinationPayload(
        id="dest_disc_hc3",
        name="Forum Token Target",
        parameters={"base_url": "http://test/discourse"},
    )
    connection = ConnectionPayload(
        base_url="http://test/discourse",
        api_key="expired_or_invalid_key",
    )

    # Script 401 unauthorized
    scenarios["discourse"] = {"status_code": 401}

    with pytest.raises(IncuBrixError) as exc_info:
        await connector.publish(rendition, destination, connection, "idemp_hc03")

    err = exc_info.value
    assert err.code == ErrorCode.CONNECTION_AUTH_EXPIRED
    assert err.retryable is False
    assert err.status_code == 401
    print(f"\n[HC3 PASS] HTTP 401 correctly translated to non-retryable CONNECTION_AUTH_EXPIRED.")
