import pytest
from connectors.lemmy.client import LemmyConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode


@pytest.fixture
def lemmy_connector() -> LemmyConnector:
    manifest = registry.get_manifest("lemmy")
    return LemmyConnector(manifest)


@pytest.mark.asyncio
async def test_lemmy_validate_success(lemmy_connector):
    rendition = Rendition(
        title="Open Source Fediverse Discussion",
        body="Discussing decentralized social architectures and ActivityPub protocols.",
    )
    destination = DestinationPayload(
        name="Technology Community",
        parameters={"base_url": "http://localhost:8536", "community_id": 1},
    )
    connection = ConnectionPayload(base_url="http://localhost:8536", token="jwt_token_123")

    res = await lemmy_connector.validate(rendition, destination, connection)
    assert res.ok is True
    assert res.violations == []


@pytest.mark.asyncio
async def test_lemmy_validate_field_level_violations(lemmy_connector):
    # Title exceeds 100 chars
    long_title = "L" * 120
    rendition = Rendition(title=long_title, body="Normal body")
    destination = DestinationPayload(name="Technology")
    connection = ConnectionPayload()

    res = await lemmy_connector.validate(rendition, destination, connection)
    assert res.ok is False
    assert any("title" in v and "100 chars" in v for v in res.violations)
    assert any("base_url" in v for v in res.violations)


@pytest.mark.asyncio
async def test_lemmy_error_mapping(lemmy_connector):
    # 401
    err_401 = lemmy_connector.map_http_status_to_error(401, "Token expired")
    assert err_401.code == ErrorCode.CONNECTION_AUTH_EXPIRED
    assert err_401.retryable is False

    # 429 with reset time
    err_429 = lemmy_connector.map_http_status_to_error(
        429, "Too many posts", headers={"Retry-After": "60"}
    )
    assert err_429.code == ErrorCode.PLATFORM_RATE_LIMIT
    assert err_429.retryable is True
    assert err_429.details.get("retry_after_seconds") == 60

    # 422
    err_422 = lemmy_connector.map_http_status_to_error(422, "Community does not allow cross-posting")
    assert err_422.code == ErrorCode.PLATFORM_CONTENT_REJECTED
    assert err_422.retryable is False

    # 500
    err_500 = lemmy_connector.map_http_status_to_error(500, "Internal error")
    assert err_500.code == ErrorCode.PLATFORM_UNAVAILABLE
    assert err_500.retryable is True
