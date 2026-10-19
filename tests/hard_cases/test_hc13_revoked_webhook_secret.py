import pytest
from httpx import AsyncClient, ASGITransport
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from connectors.signed_webhook.client import SignedWebhookConnector
from core.errors import ErrorCode, IncuBrixError
from mock_platforms.main import app as mock_platforms_app, scenarios


@pytest.fixture
def mock_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_hc13_revoked_webhook_secret_signature_failure(mock_client):
    """HC13: Partner revokes webhook signing secret or endpoint returns 403/500.

    Expected: Webhook connector detects signature/handshake failure, maps to
    PLATFORM_UNAVAILABLE or CONNECTION_AUTH_EXPIRED, ceases transmission.
    """
    scenarios.clear()
    manifest = registry.get_manifest("signed_webhook")
    connector = SignedWebhookConnector(manifest, http_client=mock_client)

    rendition = Rendition(title="Webhook Event", body='{"status": "update"}')
    destination = DestinationPayload(
        id="dest_wh_hc13",
        name="Partner Webhook",
        url="http://test/partner/webhook",
        parameters={"base_url": "http://test"},
    )
    # Using a revoked or wrong signing secret
    connection = ConnectionPayload(
        base_url="http://test",
        api_key="revoked_secret_key_invalid_0000",
    )

    # 1. Partner mock checks signature using expected shared secret; mismatch produces 401
    with pytest.raises(IncuBrixError) as exc_info:
        await connector.publish(rendition, destination, connection, "idemp_hc13_sig_fail")

    err = exc_info.value
    assert err.code == ErrorCode.CONNECTION_AUTH_EXPIRED
    assert err.status_code == 401
    print(f"\n[HC13 PASS] Signature verification failure with revoked secret caught: {err.code.value}")

    # 2. Partner endpoint returns 403 / permission revoked
    scenarios["signed_webhook"] = {"status_code": 403}
    with pytest.raises(IncuBrixError) as exc_403:
        await connector.publish(rendition, destination, connection, "idemp_hc13_403")
    assert exc_403.value.code == ErrorCode.CONNECTION_AUTH_EXPIRED

    # 3. Partner endpoint unavailable (500)
    scenarios["signed_webhook"] = {"status_code": 500}
    with pytest.raises(IncuBrixError) as exc_500:
        await connector.publish(rendition, destination, connection, "idemp_hc13_500")
    assert exc_500.value.code == ErrorCode.PLATFORM_UNAVAILABLE
    print("[HC13 PASS] Partner 403 and 500 mapped cleanly; transmission ceased.")
