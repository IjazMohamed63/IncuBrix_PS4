import base64
import json
import pytest
from connectors.ghost.client import GhostConnector, generate_ghost_admin_jwt
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode


@pytest.fixture
def ghost_connector() -> GhostConnector:
    manifest = registry.get_manifest("ghost")
    return GhostConnector(manifest)


def test_generate_ghost_admin_jwt_structure():
    # Valid key format {id}:{secret_in_hex}
    key_id = "651f4d9904bb97000109d941"
    secret_hex = "e89a696c21e646279f1d0b7414dfac86fa7984f880f08960fa236d6cf5095314"
    api_key = f"{key_id}:{secret_hex}"

    token = generate_ghost_admin_jwt(api_key)
    parts = token.split(".")
    assert len(parts) == 3

    # Verify header contains kid and HS256
    header_raw = base64.urlsafe_b64decode(parts[0] + "==")
    header = json.loads(header_raw.decode("utf-8"))
    assert header["alg"] == "HS256"
    assert header["typ"] == "JWT"
    assert header["kid"] == key_id

    # Verify payload aud and expiration
    payload_raw = base64.urlsafe_b64decode(parts[1] + "==")
    payload = json.loads(payload_raw.decode("utf-8"))
    assert payload["aud"] == "/admin/"
    assert payload["exp"] > payload["iat"]


@pytest.mark.asyncio
async def test_ghost_validate_success(ghost_connector):
    rendition = Rendition(
        title="Modern Engineering Architecture",
        body="<p>Full walkthrough of the distribution network.</p>",
    )
    destination = DestinationPayload(
        name="Ghost Engineering Blog",
        parameters={"base_url": "http://localhost:2368"},
    )
    connection = ConnectionPayload(
        base_url="http://localhost:2368",
        api_key="651f4d9904bb97000109d941:e89a696c21e646279f1d0b7414dfac86fa7984f880f08960fa236d6cf5095314",
    )

    res = await ghost_connector.validate(rendition, destination, connection)
    assert res.ok is True
    assert res.violations == []


@pytest.mark.asyncio
async def test_ghost_validate_field_level_violations(ghost_connector):
    # Empty title, empty body, missing api_key, missing base_url
    rendition = Rendition(title="", body="")
    destination = DestinationPayload(name="Ghost Blog")
    connection = ConnectionPayload()

    res = await ghost_connector.validate(rendition, destination, connection)
    assert res.ok is False
    assert any("title" in v for v in res.violations)
    assert any("body" in v for v in res.violations)
    assert any("base_url" in v for v in res.violations)
    assert any("connection" in v for v in res.violations)


@pytest.mark.asyncio
async def test_ghost_error_mapping(ghost_connector):
    # 401
    err_401 = ghost_connector.map_http_status_to_error(401, "Invalid token")
    assert err_401.code == ErrorCode.CONNECTION_AUTH_EXPIRED

    # 429
    err_429 = ghost_connector.map_http_status_to_error(
        429, "Rate limit reached", headers={"Retry-After": "50"}
    )
    assert err_429.code == ErrorCode.PLATFORM_RATE_LIMIT
    assert err_429.details.get("retry_after_seconds") == 50

    # 422
    err_422 = ghost_connector.map_http_status_to_error(422, "Slug already in use")
    assert err_422.code == ErrorCode.PLATFORM_CONTENT_REJECTED

    # 503
    err_503 = ghost_connector.map_http_status_to_error(503, "Ghost starting")
    assert err_503.code == ErrorCode.PLATFORM_UNAVAILABLE
