import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from api.main import app


@pytest.mark.asyncio
async def test_ready_endpoint_all_up():
    """Verify GET /ready returns 200 ready when DB, queue, and storage are healthy."""
    transport = ASGITransport(app=app)
    with patch("api.routers.health.check_database_health", return_value=True), \
         patch("api.routers.health.check_redis_health", return_value=True), \
         patch("api.routers.health.storage.check_health", return_value=True):

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/ready")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ready"
            assert data["checks"]["database"] == "up"
            assert data["checks"]["queue"] == "up"
            assert data["checks"]["storage"] == "up"


@pytest.mark.asyncio
async def test_ready_endpoint_service_down():
    """Verify GET /ready returns 503 not_ready when a dependency fails."""
    transport = ASGITransport(app=app)
    with patch("api.routers.health.check_database_health", return_value=False), \
         patch("api.routers.health.check_redis_health", return_value=True), \
         patch("api.routers.health.storage.check_health", return_value=True):

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/ready")
            assert res.status_code == 503
            data = res.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["database"] == "down"
            assert data["checks"]["queue"] == "up"
            assert data["checks"]["storage"] == "up"
