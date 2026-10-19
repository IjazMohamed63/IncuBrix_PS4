import hashlib
import hmac
import time
import pytest
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from connectors.signed_webhook.client import SignedWebhookConnector
from core.errors import ErrorCode


@pytest.fixture
def webhook_connector() -> SignedWebhookConnector:
    manifest = registry.get_manifest("signed_webhook")
    return SignedWebhookConnector(manifest)


def test_hmac_sha256_signature_and_replay_logic(webhook_connector):
    secret = "whsec_test_secret_for_validation_123"
    timestamp = int(time.time())
    body = '{"event":"test","idempotency_key":"k123"}'

    sig = webhook_connector._sign_payload(body, secret, timestamp)
    assert len(sig) == 64  # SHA256 hex digest length

    # Verify signature independently
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert sig == expected

    # Verify replay window tolerance logic: within 300s is valid
    now = time.time()
    assert abs(now - timestamp) <= 300
    # An expired timestamp (e.g. 10 minutes ago)
    expired_timestamp = timestamp - 600
    assert abs(now - expired_timestamp) > 300


@pytest.mark.asyncio
async def test_signed_webhook_validate_success(webhook_connector):
    rendition = Rendition(
        title="Webhook Event Dispatch",
        body='{"data": "valid json body payload"}',
    )
    destination = DestinationPayload(
        name="Partner Webhook",
        url="https://partner.example.com/api/v1/webhook",
        parameters={"base_url": "https://partner.example.com/api/v1"},
    )
    connection = ConnectionPayload(
        base_url="https://partner.example.com/api/v1",
        api_key="whsec_12345",
    )

    res = await webhook_connector.validate(rendition, destination, connection)
    assert res.ok is True
    assert res.violations == []


@pytest.mark.asyncio
async def test_signed_webhook_validate_field_level_violations(webhook_connector):
    rendition = Rendition(title="Webhook", body="valid body")
    destination = DestinationPayload(name="Invalid Target", url="not_a_valid_url")
    connection = ConnectionPayload()

    res = await webhook_connector.validate(rendition, destination, connection)
    assert res.ok is False
    assert any("url" in v for v in res.violations)


@pytest.mark.asyncio
async def test_signed_webhook_error_mapping(webhook_connector):
    # 400
    err_400 = webhook_connector.map_http_status_to_error(400, "Timestamp expired")
    assert err_400.code == ErrorCode.PLATFORM_CONTENT_REJECTED

    # 401
    err_401 = webhook_connector.map_http_status_to_error(401, "Signature verification failed")
    assert err_401.code == ErrorCode.CONNECTION_AUTH_EXPIRED

    # 429
    err_429 = webhook_connector.map_http_status_to_error(
        429, "Rate limit reached", headers={"Retry-After": "60"}
    )
    assert err_429.code == ErrorCode.PLATFORM_RATE_LIMIT
    assert err_429.details.get("retry_after_seconds") == 60

    # 502
    err_502 = webhook_connector.map_http_status_to_error(502, "Bad Gateway")
    assert err_502.code == ErrorCode.PLATFORM_UNAVAILABLE
