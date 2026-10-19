import pytest
from unittest.mock import AsyncMock
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from engine.publisher import PublishEngine
from mock_platforms.main import app as mock_platforms_app, posts_store, scenarios
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_hc01_timeout_after_accept_reconciliation(mock_client):
    """HC1: Publish call times out and is retried with identical Idempotency-Key.

    Expected: Reconcile first. Query platform status; if accepted, return existing
    post ID; never create a duplicate post.
    """
    posts_store.clear()
    scenarios.clear()

    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest, http_client=mock_client)
    publisher = PublishEngine()

    rendition = Rendition(
        title="Distributed Queue Architecture Post",
        body="Detailed discussion on message queues and timeout reconciliation.",
    )
    destination = DestinationPayload(
        id="dest_disc_hc1",
        name="Tech Forum",
        parameters={"base_url": "http://test/discourse"},
    )
    connection = ConnectionPayload(
        base_url="http://test/discourse",
        api_key="valid_api_key",
    )
    idempotency_key = "idemp_hc01_reconcile_999"

    # Step 1: Script platform scenario: timeout after post accepted
    scenarios["discourse"] = {"timeout_after_accept": True}

    # Step 2: Publish request is sent. Platform accepts and creates the post, but gateway times out (504).
    # PublishEngine intercepts the timeout, runs reconciliation, and successfully recovers the post!
    res = await publisher.publish(
        rendition=rendition,
        destination=destination,
        connection=connection,
        idempotency_key=idempotency_key,
        connector_override=connector,
    )

    assert res["status"] == "published"
    assert res.get("reconciled") is True
    post_id = res["platform_post_id"]
    assert post_id != ""

    # Verify that exactly ONE post exists on platform (no duplicates created)
    discourse_posts = [k for k in posts_store.keys() if k.startswith("discourse_")]
    assert len(discourse_posts) == 1, f"Expected exactly 1 post, found {len(discourse_posts)}"

    # Step 3: Subsequent call with identical Idempotency-Key returns cached response without duplicate post
    res_retry = await publisher.publish(
        rendition=rendition,
        destination=destination,
        connection=connection,
        idempotency_key=idempotency_key,
        connector_override=connector,
    )
    assert res_retry["platform_post_id"] == post_id
    assert len([k for k in posts_store.keys() if k.startswith("discourse_")]) == 1
    print(f"\n[HC1 PASS] Successfully reconciled timeout: Post ID {post_id}, zero duplicate posts.")
