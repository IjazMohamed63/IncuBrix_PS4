import pytest
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError


@pytest.fixture
def discourse_connector() -> DiscourseConnector:
    manifest = registry.get_manifest("discourse")
    return DiscourseConnector(manifest)


@pytest.mark.asyncio
async def test_discourse_validate_success(discourse_connector):
    rendition = Rendition(
        title="Valid Discussion Topic on AI",
        body="This is a detailed topic body exceeding the minimum required character length.",
    )
    destination = DestinationPayload(
        name="Discourse AI Forum",
        parameters={"base_url": "http://discourse.local"},
    )
    connection = ConnectionPayload(base_url="http://discourse.local", api_key="test_key")

    res = await discourse_connector.validate(rendition, destination, connection)
    assert res.ok is True
    assert res.violations == []


@pytest.mark.asyncio
async def test_discourse_validate_field_level_violations(discourse_connector):
    # Short title (<5 chars), short body (<10 chars), missing base_url
    rendition = Rendition(title="Hi", body="Short")
    destination = DestinationPayload(name="Discourse AI Forum")
    connection = ConnectionPayload()

    res = await discourse_connector.validate(rendition, destination, connection)
    assert res.ok is False
    assert len(res.violations) == 3
    assert any("base_url" in v for v in res.violations)
    assert any("title" in v for v in res.violations)
    assert any("body" in v for v in res.violations)


@pytest.mark.asyncio
async def test_discourse_error_mapping(discourse_connector):
    # Test 401
    err_401 = discourse_connector.map_http_status_to_error(401, "Invalid API key")
    assert err_401.code == ErrorCode.CONNECTION_AUTH_EXPIRED
    assert err_401.retryable is False

    # Test 429 with reset time
    err_429 = discourse_connector.map_http_status_to_error(
        429, "Rate limit exceeded", headers={"Retry-After": "45"}
    )
    assert err_429.code == ErrorCode.PLATFORM_RATE_LIMIT
    assert err_429.retryable is True
    assert err_429.details.get("retry_after_seconds") == 45

    # Test 422
    err_422 = discourse_connector.map_http_status_to_error(422, "Title already exists")
    assert err_422.code == ErrorCode.PLATFORM_CONTENT_REJECTED
    assert err_422.retryable is False

    # Test 503
    err_503 = discourse_connector.map_http_status_to_error(503, "Discourse rebuilding")
    assert err_503.code == ErrorCode.PLATFORM_UNAVAILABLE
    assert err_503.retryable is True
