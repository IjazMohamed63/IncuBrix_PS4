import pytest
from httpx import AsyncClient, ASGITransport

from connectors.assisted.client import AssistedConnector
from connectors.devto.client import DevtoConnector
from connectors.discourse.client import DiscourseConnector
from connectors.ghost.client import GhostConnector
from connectors.lemmy.client import LemmyConnector
from connectors.registry import registry
from connectors.schemas import (
    ConnectionPayload,
    DestinationPayload,
    MediaItem,
    Rendition,
)
from connectors.signed_webhook.client import SignedWebhookConnector
from core.errors import ErrorCode, IncuBrixError
from mock_platforms.main import app as mock_platforms_app, posts_store, scenarios


@pytest.fixture
def mock_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def clean_state():
    posts_store.clear()
    scenarios.clear()
    yield
    posts_store.clear()
    scenarios.clear()


# =====================================================================
# 1. DISCOURSE CERTIFICATION: validate -> publish -> get_status -> delete
# =====================================================================

@pytest.mark.asyncio
async def test_discourse_certification_lifecycle(mock_client):
    """Certifies Discourse connector against mock Discourse REST API."""
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest, http_client=mock_client)

    rendition = Rendition(
        title="Scaling Video Models on Federated Infrastructure",
        body="Detailed discussion on GPU latency, quantization, and real-time distributed inference pipelines.",
    )
    destination = DestinationPayload(
        id="dest_disc_01",
        name="AI & Video Architecture Forum",
        parameters={"base_url": "http://test/discourse", "category_id": 5},
    )
    connection = ConnectionPayload(
        base_url="http://test/discourse",
        api_key="discourse_test_api_key_xyz",
        extra={"username": "incubrix_bot"},
    )

    # Step 1: Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True, f"Validation failed: {val.violations}"

    # Step 2: Publish
    pub = await connector.publish(rendition, destination, connection, "idemp_disc_001")
    assert pub.status == "published"
    assert pub.platform_post_id != ""
    assert "discourse" in pub.live_url
    print(f"\n[DISCOURSE] Published Post ID: {pub.platform_post_id}, Live URL: {pub.live_url}")

    # Step 3: Get Status (Confirm Live)
    status_res = await connector.get_status(pub.platform_post_id, connection)
    assert status_res.status == "active"
    assert status_res.live_url == pub.live_url
    print(f"[DISCOURSE] Status Checked: {status_res.status}, Live URL: {status_res.live_url}")

    # Step 4: Delete (Within 10 minutes cleanup rule)
    del_res = await connector.delete(pub.platform_post_id, connection)
    assert del_res.deleted is True
    print(f"[DISCOURSE] Post {pub.platform_post_id} deleted successfully.")


# =====================================================================
# 2. LEMMY CERTIFICATION: validate -> publish -> get_status -> delete
# =====================================================================

@pytest.mark.asyncio
async def test_lemmy_certification_lifecycle(mock_client):
    """Certifies Lemmy connector against Lemmy HTTP API v3."""
    manifest = registry.get_manifest("lemmy")
    connector = LemmyConnector(manifest, http_client=mock_client)

    rendition = Rendition(
        title="Decentralized Distribution Protocols",
        body="Exploring federated community architectures and ActivityPub protocol distribution across Lemmy.",
        canonical_url="https://incubrix.com/blog/federated-protocols",
    )
    destination = DestinationPayload(
        id="dest_lemmy_01",
        name="Technology Community",
        parameters={"base_url": "http://test/lemmy", "community_id": 1},
    )
    connection = ConnectionPayload(
        base_url="http://test/lemmy",
        token="lemmy_bot_jwt_token_sample",
    )

    # Step 1: Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True, f"Validation failed: {val.violations}"

    # Step 2: Publish
    pub = await connector.publish(rendition, destination, connection, "idemp_lemmy_001")
    assert pub.status == "published"
    assert pub.platform_post_id != ""
    assert "post" in pub.live_url
    print(f"\n[LEMMY] Published Post ID: {pub.platform_post_id}, Live URL: {pub.live_url}")

    # Step 3: Get Status
    status_res = await connector.get_status(pub.platform_post_id, connection)
    assert status_res.status == "active"
    assert status_res.live_url == pub.live_url
    print(f"[LEMMY] Status Checked: {status_res.status}, Live URL: {status_res.live_url}")

    # Step 4: Delete
    del_res = await connector.delete(pub.platform_post_id, connection)
    assert del_res.deleted is True
    print(f"[LEMMY] Post {pub.platform_post_id} deleted successfully.")


# =====================================================================
# 3. DEVTO CERTIFICATION: validate -> publish -> get_status -> delete
# =====================================================================

@pytest.mark.asyncio
async def test_devto_certification_lifecycle(mock_client):
    """Certifies Dev.to connector against mock Forem server (labelled mock, never real)."""
    manifest = registry.get_manifest("devto")
    connector = DevtoConnector(manifest, http_client=mock_client)

    rendition = Rendition(
        title="Microservices Event Delivery With Signed Webhooks",
        body="## Reliable Webhook Delivery\n\nHow to design secure, HMAC-signed webhooks with replay protection.",
        tags=["python", "security", "webdev"],
        canonical_url="https://incubrix.com/blog/signed-webhooks",
    )
    destination = DestinationPayload(
        id="dest_devto_01",
        name="Dev.to Technical Publishing",
        parameters={"base_url": "http://test/devto"},
    )
    connection = ConnectionPayload(
        base_url="http://test/devto",
        api_key="mock_devto_api_key_sample",
    )

    # Step 1: Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True, f"Validation failed: {val.violations}"

    # Step 2: Publish
    pub = await connector.publish(rendition, destination, connection, "idemp_devto_001")
    assert pub.status == "published"
    assert pub.platform_post_id != ""
    # Ensure result is from mock server and labelled clearly
    assert "mock.devto" in pub.live_url or "test/devto" in pub.live_url
    print(f"\n[DEVTO - MOCK] Published Article ID: {pub.platform_post_id}, Live URL: {pub.live_url} (mock environment)")

    # Step 3: Get Status
    status_res = await connector.get_status(pub.platform_post_id, connection)
    assert status_res.status == "active"
    assert status_res.live_url == pub.live_url
    print(f"[DEVTO - MOCK] Status Checked: {status_res.status}, Live URL: {status_res.live_url}")

    # Step 4: Delete
    del_res = await connector.delete(pub.platform_post_id, connection)
    assert del_res.deleted is True
    print(f"[DEVTO - MOCK] Article {pub.platform_post_id} deleted successfully.")


# =====================================================================
# 4. GHOST CERTIFICATION: validate -> publish -> get_status -> delete
# =====================================================================

@pytest.mark.asyncio
async def test_ghost_certification_lifecycle(mock_client):
    """Certifies Ghost connector using Admin API with short-lived JWT authentication."""
    manifest = registry.get_manifest("ghost")
    connector = GhostConnector(manifest, http_client=mock_client)

    rendition = Rendition(
        title="Engineering Assessment: Long-Tail Distribution Architecture",
        body="<p>Comprehensive overview of stateless connectors and multi-instance catalogue scaling.</p>",
        tags=["architecture", "engineering"],
        canonical_url="https://incubrix.com/blog/assessment4",
    )
    destination = DestinationPayload(
        id="dest_ghost_01",
        name="Ghost Engineering Blog",
        parameters={"base_url": "http://test/ghost"},
    )
    connection = ConnectionPayload(
        base_url="http://test/ghost",
        api_key="651f4d9904bb97000109d941:e89a696c21e646279f1d0b7414dfac86fa7984f880f08960fa236d6cf5095314",
    )

    # Step 1: Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True, f"Validation failed: {val.violations}"

    # Step 2: Publish (verifies JWT creation and transmission)
    pub = await connector.publish(rendition, destination, connection, "idemp_ghost_001")
    assert pub.status == "published"
    assert pub.platform_post_id != ""
    print(f"\n[GHOST] Published Post ID: {pub.platform_post_id}, Live URL: {pub.live_url}")

    # Step 3: Get Status
    status_res = await connector.get_status(pub.platform_post_id, connection)
    assert status_res.status == "active"
    print(f"[GHOST] Status Checked: {status_res.status}, Live URL: {status_res.live_url}")

    # Step 4: Delete
    del_res = await connector.delete(pub.platform_post_id, connection)
    assert del_res.deleted is True
    print(f"[GHOST] Post {pub.platform_post_id} deleted successfully.")


# =====================================================================
# 5. SIGNED WEBHOOK CERTIFICATION: validate -> publish -> get_status -> delete
# =====================================================================

@pytest.mark.asyncio
async def test_signed_webhook_certification_lifecycle(mock_client):
    """Certifies Signed Webhook connector with HMAC-SHA256, timestamp replay check, and secret protection."""
    manifest = registry.get_manifest("signed_webhook")
    connector = SignedWebhookConnector(manifest, http_client=mock_client)

    rendition = Rendition(
        title="Content Syndication Event",
        body='{"event": "publication", "creator": "IncuBrix", "reach": 15000}',
    )
    destination = DestinationPayload(
        id="dest_webhook_01",
        name="Syndication Partner Webhook",
        url="http://test/partner/webhook",
        parameters={"base_url": "http://test"},
    )
    connection = ConnectionPayload(
        base_url="http://test",
        api_key="test_webhook_secret_key_12345",
    )

    # Step 1: Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True, f"Validation failed: {val.violations}"

    # Step 2: Publish (sends HMAC-SHA256 signature and timestamp; partner mock verifies)
    pub = await connector.publish(rendition, destination, connection, "idemp_webhook_001")
    assert pub.status == "published"
    assert pub.platform_post_id.startswith("wh_")
    print(f"\n[SIGNED WEBHOOK] Delivery ID: {pub.platform_post_id}, Receipt URL: {pub.live_url}")

    # Step 3: Get Status
    status_res = await connector.get_status(pub.platform_post_id, connection)
    assert status_res.status == "active"
    print(f"[SIGNED WEBHOOK] Status Checked: {status_res.status}, Receipt URL: {status_res.live_url}")

    # Step 4: Delete / Cancellation
    del_res = await connector.delete(pub.platform_post_id, connection)
    assert del_res.deleted is True
    print(f"[SIGNED WEBHOOK] Delivery {pub.platform_post_id} cancelled/deleted successfully.")


# =====================================================================
# 6. ASSISTED PACK CERTIFICATION: validate -> build_assist_pack -> verify never published
# =====================================================================

@pytest.mark.asyncio
async def test_assisted_certification_lifecycle():
    """Certifies Assisted connector: builds complete assist pack, strictly enforces never reported as published."""
    manifest = registry.get_manifest("assisted")
    connector = AssistedConnector(manifest)

    rendition = Rendition(
        title="Launching our Long-Tail Distribution Architecture",
        body="We spent 2 weeks building stateless connectors and certification watchdogs. Here is what we learned.",
        media=[
            MediaItem(url="http://cdn.incubrix.com/diagram_c4.png", media_type="image/png"),
            MediaItem(url="http://cdn.incubrix.com/benchmark_report.pdf", media_type="application/pdf"),
        ],
        ai_disclosure="Outlined with Gemini 3.8 Flash assistance.",
    )
    destination = DestinationPayload(
        id="dest_assisted_01",
        name="Indie Hackers Product Showcase",
        url="https://indiehackers.com/post/new",
        automation_allowed=False,
    )
    connection = ConnectionPayload(auth_type="none")

    # Step 1: Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True, f"Validation failed: {val.violations}"

    # Step 2: Build Assist Pack
    pack = await connector.build_assist_pack(rendition, destination)
    assert len(pack.files) == 2
    assert "diagram_c4.png" in pack.files[0]
    assert "benchmark_report.pdf" in pack.files[1]
    assert "Launching our Long-Tail Distribution Architecture" in pack.caption
    assert "Gemini 3.8 Flash" in pack.caption
    assert pack.deep_link == "https://indiehackers.com/post/new"
    assert len(pack.checklist) == 4
    print(f"\n[ASSISTED] Assist Pack Generated with {len(pack.files)} media files, deep link: {pack.deep_link}")
    print(f"[ASSISTED] Checklist items required: {[c.id for c in pack.checklist]}")

    # Step 3: Crucial Specification Proof - Package creation is NEVER reported as 'published'
    with pytest.raises(IncuBrixError) as exc_info:
        await connector.publish(rendition, destination, connection, "idemp_assist_001")
    assert exc_info.value.code == ErrorCode.DEST_SPEC_VIOLATION
    assert "never reported as 'published'" in exc_info.value.message or "build_assist_pack" in exc_info.value.message
    print("[ASSISTED] Confirmed: Automated publish is blocked with DEST_SPEC_VIOLATION; never reported as 'published'.")
