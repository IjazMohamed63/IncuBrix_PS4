import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import tempfile
import yaml

from api.main import app
from connectors.registry import registry
from core.errors import ErrorCode


@pytest.fixture(autouse=True)
def ensure_connector_active():
    """Ensures stub connector is enabled before each test."""
    registry.enable_connector("stub")
    yield
    registry.enable_connector("stub")


@pytest.mark.asyncio
async def test_health_check_and_correlation_id():
    """Verify GET /health returns 200 pass and includes X-Correlation-Id header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health", headers={"X-Correlation-Id": "test_corr_12345"})
        assert res.status_code == 200
        assert res.json() == {"status": "pass"}
        assert res.headers.get("X-Correlation-Id") == "test_corr_12345"


@pytest.mark.asyncio
async def test_validate_method_success():
    """Verify POST /connector/v1/stub/validate returns {ok: True, violations: []} for valid content."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rendition": {
                "title": "Clean Title Under Limit",
                "body": "Body content within limit",
                "canonical_url": "https://example.com/blog/test",
                "tags": ["ai", "saas"],
            },
            "destination": {
                "id": "dest_123",
                "name": "Test Forum",
                "platform_key": "stub",
            },
            "connection": {
                "auth_type": "api_key",
                "api_key": "test_key",
                "base_url": "http://stub.local",
            },
        }
        res = await client.post("/connector/v1/stub/validate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["violations"] == []


@pytest.mark.asyncio
async def test_validate_method_violations():
    """Verify validate reports field-level spec violations when limits are breached."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rendition": {
                "title": "A" * 250,  # Manifest limit is 200
                "body": "B" * 6000,  # Manifest limit is 5000
            },
            "destination": {"name": "Test Forum"},
            "connection": {"auth_type": "none"},
        }
        res = await client.post("/connector/v1/stub/validate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is False
        assert len(data["violations"]) == 2
        assert "Title exceeds" in data["violations"][0]
        assert "Body exceeds" in data["violations"][1]


@pytest.mark.asyncio
async def test_publish_method_success():
    """Verify POST /connector/v1/stub/publish returns platform_post_id, live_url, status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rendition": {
                "title": "Valid Post Title",
                "body": "Valid body content",
            },
            "destination": {"name": "Test Forum"},
            "connection": {"base_url": "http://stub.local"},
            "idempotency_key": "idemp_test_9999",
        }
        res = await client.post("/connector/v1/stub/publish", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["platform_post_id"] == "stub_post_idemp_te"
        assert data["live_url"] == "http://stub.local/posts/stub_post_idemp_te"
        assert data["status"] == "published"


@pytest.mark.asyncio
async def test_get_status_method():
    """Verify POST /connector/v1/stub/get_status returns post status and live_url."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "platform_post_id": "post_789",
            "connection": {"base_url": "http://stub.local"},
        }
        res = await client.post("/connector/v1/stub/get_status", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "active"
        assert data["live_url"] == "http://stub.local/posts/post_789"


@pytest.mark.asyncio
async def test_delete_method():
    """Verify POST /connector/v1/stub/delete returns deleted: true."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "platform_post_id": "post_789",
            "connection": {},
        }
        res = await client.post("/connector/v1/stub/delete", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["deleted"] is True


@pytest.mark.asyncio
async def test_fetch_metrics_method():
    """Verify POST /connector/v1/stub/fetch_metrics returns engagement metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "platform_post_id": "post_789",
            "connection": {},
        }
        res = await client.post("/connector/v1/stub/fetch_metrics", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["views"] == 1250
        assert data["likes"] == 45
        assert data["clicks"] == 110


@pytest.mark.asyncio
async def test_refresh_auth_method():
    """Verify POST /connector/v1/stub/refresh_auth returns expires_at."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"connection": {}}
        res = await client.post("/connector/v1/stub/refresh_auth", json=payload)
        assert res.status_code == 200
        assert "expires_at" in res.json()


@pytest.mark.asyncio
async def test_build_assist_pack_method():
    """Verify POST /connector/v1/stub/build_assist_pack returns assist bundle."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rendition": {
                "title": "Manual Post Title",
                "body": "Discussion topic for high-trust community",
                "media": [{"url": "http://media.local/image.png", "media_type": "image/png"}],
            },
            "destination": {
                "url": "https://community.example.com/new-post",
            },
        }
        res = await client.post("/connector/v1/stub/build_assist_pack", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "image.png" in data["files"][0]
        assert data["caption"].startswith("Manual Post Title")
        assert len(data["checklist"]) >= 2


@pytest.mark.asyncio
async def test_unknown_method_returns_404():
    """Verify invoking an unsupported method returns 404 with standard error body."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/connector/v1/stub/unknown_action", json={})
        assert res.status_code == 404
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["retryable"] is False


@pytest.mark.asyncio
async def test_connector_kill_switch():
    """Verify CONNECTOR_DISABLED error is returned when kill switch is enabled."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        registry.disable_connector("stub")
        try:
            res = await client.post("/connector/v1/stub/publish", json={
                "rendition": {"title": "T", "body": "B"},
                "destination": {},
                "connection": {},
                "idempotency_key": "k",
            })
            assert res.status_code == 403
            data = res.json()
            assert data["error"]["code"] == "CONNECTOR_DISABLED"
            assert data["error"]["retryable"] is False
        finally:
            registry.enable_connector("stub")


@pytest.mark.asyncio
async def test_error_map_rate_limit():
    """Verify platform HTTP 429 maps to PLATFORM_RATE_LIMIT error code."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rendition": {
                "title": "Test Title",
                "body": "Test Body",
                "custom_fields": {"simulate_http_status": 429},
            },
            "destination": {},
            "connection": {},
            "idempotency_key": "k429",
        }
        res = await client.post("/connector/v1/stub/publish", json=payload)
        assert res.status_code == 429
        data = res.json()
        assert data["error"]["code"] == "PLATFORM_RATE_LIMIT"
        assert data["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_manifest_validation_rejection():
    """Verify manifest loader strictly rejects malformed manifests."""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        # Invalid manifest missing required tier and surfaces
        yaml.dump({"key": "bad_connector", "version": "1.0.0"}, f)
        temp_path = Path(f.name)

    try:
        with pytest.raises(Exception) as exc_info:
            registry.load_manifest_from_path(temp_path)
        assert "errors detected" in str(exc_info.value)
    finally:
        temp_path.unlink()
