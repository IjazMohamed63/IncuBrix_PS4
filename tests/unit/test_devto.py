import pytest
from connectors.devto.client import DevtoConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode


@pytest.fixture
def devto_connector() -> DevtoConnector:
    manifest = registry.get_manifest("devto")
    return DevtoConnector(manifest)


@pytest.mark.asyncio
async def test_devto_validate_success(devto_connector):
    rendition = Rendition(
        title="Building Distributed Webhooks",
        body="## Architecture Overview\n\nDetailed breakdown of event distribution and signature verification.",
        tags=["python", "webdev", "architecture"],
    )
    destination = DestinationPayload(name="Dev.to Community")
    connection = ConnectionPayload(api_key="test_key")

    res = await devto_connector.validate(rendition, destination, connection)
    assert res.ok is True
    assert res.violations == []


@pytest.mark.asyncio
async def test_devto_validate_field_level_violations(devto_connector):
    # Title > 128 chars, body < 20 chars, tags > 4
    rendition = Rendition(
        title="D" * 150,
        body="Too short",
        tags=["one", "two", "three", "four", "five"],
    )
    destination = DestinationPayload(name="Dev.to")
    connection = ConnectionPayload()

    res = await devto_connector.validate(rendition, destination, connection)
    assert res.ok is False
    assert len(res.violations) == 3
    assert any("title" in v and "128 chars" in v for v in res.violations)
    assert any("body" in v and "20 characters" in v for v in res.violations)
    assert any("tags" in v and "maximum of 4 tags" in v for v in res.violations)


@pytest.mark.asyncio
async def test_devto_error_mapping(devto_connector):
    # 401
    err_401 = devto_connector.map_http_status_to_error(401, "Invalid API key")
    assert err_401.code == ErrorCode.CONNECTION_AUTH_EXPIRED
    assert err_401.retryable is False

    # 429
    err_429 = devto_connector.map_http_status_to_error(
        429, "Rate limit reached", headers={"Retry-After": "30"}
    )
    assert err_429.code == ErrorCode.PLATFORM_RATE_LIMIT
    assert err_429.retryable is True
    assert err_429.details.get("retry_after_seconds") == 30

    # 422
    err_422 = devto_connector.map_http_status_to_error(422, "Tags contain forbidden terms")
    assert err_422.code == ErrorCode.PLATFORM_CONTENT_REJECTED

    # 503
    err_503 = devto_connector.map_http_status_to_error(503, "Dev.to maintenance")
    assert err_503.code == ErrorCode.PLATFORM_UNAVAILABLE
