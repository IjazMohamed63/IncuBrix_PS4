import asyncio
import io
import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from core.errors import IncuBrixError
from core.jobs import PersistentJobManager, job_manager
from core.ssrf import validate_url_ssrf_safe
from mock_platforms.main import app as mock_platforms_app, posts_store, scenarios


@pytest.fixture
def mock_platform_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def api_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest.fixture(autouse=True)
def clean_state():
    posts_store.clear()
    scenarios.clear()
    yield
    posts_store.clear()
    scenarios.clear()


@pytest.mark.asyncio
async def test_e2e_publish_lifecycle_and_output_manifest(api_client):
    """E2E Test: Full publishing lifecycle via POST /api/v1/publish, job status, and manifest verification."""
    # 1. Register destination in catalogue
    dest_payload = {
        "id": "e2e_dest_devto",
        "name": "E2E Dev.to Community",
        "url": "http://test/devto",
        "platform_key": "devto",
        "connector_key": "devto",
        "surface": "article",
        "parameters": {"base_url": "http://test/devto"},
        "connection": {
            "base_url": "http://test/devto",
            "api_key": "e2e_devto_test_key_12345",
        },
    }
    create_dest_res = await api_client.post("/api/v1/destinations", json=dest_payload)
    assert create_dest_res.status_code == 201
    created_dest = create_dest_res.json()
    dest_id = created_dest["id"]

    # 2. Publish Content with Idempotency-Key
    publish_payload = {
        "destination_ids": [dest_id],
        "rendition": {
            "title": "E2E Testing Long-Tail Distribution Architecture",
            "body": "## Full End to End Verification\n\nTesting stateless publishing, background jobs, and manifests.",
            "tags": ["e2e", "testing", "architecture"],
            "ai_disclosure": "Written with automated assistance.",
        },
    }
    idempotency_key = "idemp_e2e_publish_001"
    headers = {"Idempotency-Key": idempotency_key}

    pub_res = await api_client.post("/api/v1/publish", json=publish_payload, headers=headers)
    assert pub_res.status_code == 202
    data = pub_res.json()

    assert data["job_id"] is not None
    job_id = data["job_id"]

    # 3. Verify Output Manifest on result
    manifest = data.get("manifest") or data.get("details", {}).get("manifest")
    assert manifest is not None, "Output manifest JSON must be present on every result"
    assert manifest["providers"]["connector"] == "devto"
    assert manifest["ai_generated"] is True
    # Unknown values default to "unknown"
    assert manifest["cost_estimate"] == "unknown"
    assert manifest["seed"] == "unknown"

    # 4. Check Background Job Endpoint GET /api/v1/jobs/{job_id}
    job_res = await api_client.get(f"/api/v1/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["job_id"] == job_id
    assert job_data["status"] in ("queued", "running", "succeeded")
    assert 0 <= job_data["progress"] <= 100


@pytest.mark.asyncio
async def test_e2e_durable_jobs_survive_worker_restart(tmp_path):
    """E2E Test: Proves durable background jobs survive an API / worker restart."""
    db_file = tmp_path / "test_jobs_restart.db"

    # Worker instance 1 creates job
    worker_1 = PersistentJobManager(db_path=str(db_file))
    job_id = worker_1.create_job(
        payload={"task": "e2e_distribution", "batch_size": 50},
        idempotency_key="idemp_restart_test_999",
        callback_url="http://test/callback",
    )
    worker_1.update_progress(job_id, 45, status="running")

    # Simulate crash / process restart
    del worker_1

    # Worker instance 2 boots up pointing to same persistent SQLite database
    worker_2 = PersistentJobManager(db_path=str(db_file))
    reloaded_job = worker_2.get_job(job_id)

    assert reloaded_job is not None, "Job must survive restart"
    assert reloaded_job["job_id"] == job_id
    assert reloaded_job["progress"] == 45
    assert reloaded_job["status"] == "running"
    assert reloaded_job["callback_url"] == "http://test/callback"

    # Worker 2 resumes and completes job
    await worker_2.complete_job(
        job_id,
        result={"published": True, "items": 50},
        result_links={"live_url": "https://example.com/post/999"},
    )

    final_job = worker_2.get_job(job_id)
    assert final_job["status"] == "succeeded"
    assert final_job["progress"] == 100
    assert final_job["result_links"]["live_url"] == "https://example.com/post/999"


@pytest.mark.asyncio
async def test_e2e_files_upload_and_ssrf_blocking(api_client):
    """E2E Test: File upload, size limit, SSRF protection against private and metadata IPs."""
    # 1. Direct File Upload
    file_bytes = b"Hello IncuBrix distribution network artifacts"
    files = {"file": ("artifact.txt", io.BytesIO(file_bytes), "text/plain")}
    res = await api_client.post("/api/v1/files/upload", files=files)
    assert res.status_code == 201
    file_data = res.json()
    assert file_data["filename"] == "artifact.txt"
    assert file_data["size_bytes"] == len(file_bytes)
    assert "download_url" in file_data
    assert "manifest" in file_data

    # 2. SSRF Protection: Loopback IP (127.0.0.1)
    with pytest.raises(IncuBrixError) as exc_info:
        validate_url_ssrf_safe("http://127.0.0.1:8000/internal-secret")
    assert exc_info.value.status_code == 403
    assert "SSRF violation" in exc_info.value.message

    # 3. SSRF Protection: AWS Cloud Metadata (169.254.169.254)
    with pytest.raises(IncuBrixError) as exc_info:
        validate_url_ssrf_safe("http://169.254.169.254/latest/meta-data/")
    assert exc_info.value.status_code == 403
    assert "prohibited host" in exc_info.value.message or "SSRF violation" in exc_info.value.message

    # 4. SSRF Protection: Private RFC1918 (10.0.0.1)
    with pytest.raises(IncuBrixError) as exc_info:
        validate_url_ssrf_safe("http://10.0.0.1/admin")
    assert exc_info.value.status_code == 403
