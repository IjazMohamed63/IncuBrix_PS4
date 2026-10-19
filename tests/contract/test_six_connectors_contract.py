import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from connectors.registry import registry
from core.errors import ErrorCode

CORE_CONNECTORS = ["discourse", "lemmy", "devto", "ghost", "signed_webhook", "assisted"]


@pytest.fixture(autouse=True)
def enable_all_connectors():
    for key in CORE_CONNECTORS:
        registry.enable_connector(key)
    yield
    for key in CORE_CONNECTORS:
        registry.enable_connector(key)


@pytest.mark.asyncio
@pytest.mark.parametrize("connector_key", CORE_CONNECTORS)
async def test_connector_registered_and_manifest_valid(connector_key: str):
    """Verify each core connector is registered and adheres to ConnectorManifest schema."""
    manifest = registry.get_manifest(connector_key)
    assert manifest.key == connector_key
    assert manifest.version == "1.0.0"
    assert manifest.tier in ["native", "protocol", "bridge", "assisted", "feed"]
    assert len(manifest.surfaces) >= 1
    assert manifest.rate_limits.per_connection.requests > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("connector_key", CORE_CONNECTORS)
async def test_connector_kill_switch_contract(connector_key: str):
    """Verify kill switch returns 403 CONNECTOR_DISABLED across all connectors."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        registry.disable_connector(connector_key)
        try:
            payload = {
                "rendition": {"title": "Test Title", "body": "Test Body Content"},
                "destination": {"name": "Dest"},
                "connection": {},
            }
            res = await client.post(f"/connector/v1/{connector_key}/validate", json=payload)
            assert res.status_code == 403
            data = res.json()
            assert data["error"]["code"] == "CONNECTOR_DISABLED"
            assert data["error"]["retryable"] is False
        finally:
            registry.enable_connector(connector_key)


@pytest.mark.asyncio
@pytest.mark.parametrize("connector_key", CORE_CONNECTORS)
async def test_connector_validate_contract(connector_key: str):
    """Verify POST /connector/v1/{connector_key}/validate returns ok and violations list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rendition": {
                "title": "A Great Long-Tail Content Title",
                "body": "This is a comprehensive body text that satisfies length requirements.",
            },
            "destination": {
                "name": "Target Platform",
                "parameters": {"base_url": "http://platform.local"},
            },
            "connection": {
                "base_url": "http://platform.local",
                "api_key": "651f4d9904bb97000109d941:e89a696c21e646279f1d0b7414dfac86fa7984f880f08960fa236d6cf5095314",
            },
        }
        res = await client.post(f"/connector/v1/{connector_key}/validate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "ok" in data
        assert isinstance(data["violations"], list)


@pytest.mark.asyncio
async def test_assisted_connector_contract_build_assist_pack():
    """Verify POST /connector/v1/assisted/build_assist_pack conforms to contract schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rendition": {
                "title": "Manual Distribution Post",
                "body": "Quality content for community members.",
                "media": [{"url": "http://media.local/shot.png", "media_type": "image/png"}],
                "ai_disclosure": "Written with AI assistance",
            },
            "destination": {
                "name": "Private Community",
                "url": "https://community.local/submit",
            },
        }
        res = await client.post("/connector/v1/assisted/build_assist_pack", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "files" in data
        assert "caption" in data
        assert "deep_link" in data
        assert "checklist" in data
        assert len(data["checklist"]) >= 4


@pytest.mark.asyncio
async def test_assisted_connector_rejects_publish():
    """Verify assisted connector strictly rejects automated publishing and never reports 'published'."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rendition": {"title": "Title", "body": "Body"},
            "destination": {"name": "Dest"},
            "connection": {},
            "idempotency_key": "k_assisted_123",
        }
        res = await client.post("/connector/v1/assisted/publish", json=payload)
        assert res.status_code == 422
        data = res.json()
        assert data["error"]["code"] == "DEST_SPEC_VIOLATION"
        assert "never reported as 'published'" in data["error"]["message"] or "build_assist_pack" in data["error"]["message"]
