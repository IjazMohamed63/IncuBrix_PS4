import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from connectors.registry import registry
from mock_platforms.main import app as mock_platforms_app, posts_store


@pytest.fixture
def mock_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_add_second_discourse_destination_via_api_and_publish(mock_client):
    """PROVE IT REQUIREMENT:

    Adding a second instance of any type must need only a catalogue row.
    Prove it with a test that adds a new Discourse destination via the API
    and publishes to it with zero code changes.
    """
    posts_store.clear()

    # Route connector HTTP requests to the mock server transport
    discourse_conn = registry.get_connector("discourse")
    original_client = getattr(discourse_conn, "_http_client", None)
    discourse_conn._http_client = mock_client

    api_transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=api_transport, base_url="http://test") as client:
            # 1. Add a second Discourse destination via the API (1 catalogue row)
            destination_payload = {
                "name": "Discourse Founders Hub #42",
                "url": "http://test/discourse",
                "platform_key": "discourse",
                "connector_key": "discourse",
                "surface": "topic",
                "category": "founders",
                "audience_tags": ["founders", "saas", "ai"],
                "language": "en",
                "geo": "global",
                "est_audience": 35000,
                "frequency_cap": 24,
                "self_promo_allowed": True,
                "link_policy": "allowed",
                "disclosure_required": False,
                "automation_allowed": True,
                "parameters": {
                  "base_url": "http://test/discourse",
                  "category_id": 42
                },
                "connection": {
                  "auth_type": "api_key",
                  "api_key": "disc_sec_forum42_secret_key",
                  "base_url": "http://test/discourse",
                  "extra": {
                    "username": "founder_bot"
                  }
                }
            }

            create_res = await client.post("/api/v1/destinations", json=destination_payload)
            assert create_res.status_code == 201, f"Failed to create destination: {create_res.text}"
            destination_row = create_res.json()
            dest_id = destination_row["id"]
            assert dest_id != ""
            assert destination_row["name"] == "Discourse Founders Hub #42"
            print(f"\n[CATALOGUE PROOF] Created new destination row #{dest_id}: '{destination_row['name']}'")

            # 2. Publish to this new destination with ZERO code changes
            publish_payload = {
                "rendition": {
                    "title": "Scaling Distribution to 10k Creators",
                    "body": "In-depth case study on long-tail forum syndication and pre-flight posting rules.",
                },
                "idempotency_key": "idemp_dyn_disc_42_001",
            }

            pub_res = await client.post(f"/api/v1/destinations/{dest_id}/publish", json=publish_payload)
            assert pub_res.status_code == 200, f"Publish failed: {pub_res.text}"
            pub_data = pub_res.json()
            assert pub_data["status"] == "published"
            assert pub_data["platform_post_id"] != ""
            assert "discourse" in pub_data["live_url"]
            print(f"[CATALOGUE PROOF] Published post to Forum #42 successfully!")
            print(f"                 Platform Post ID: {pub_data['platform_post_id']}")
            print(f"                 Live URL: {pub_data['live_url']}")

            # 3. Verify status through the connector contract
            status_res = await client.post("/connector/v1/discourse/get_status", json={
                "platform_post_id": pub_data["platform_post_id"],
                "connection": destination_payload["connection"],
            })
            assert status_res.status_code == 200
            status_data = status_res.json()
            assert status_data["status"] == "active"
            print(f"[CATALOGUE PROOF] Status verified: {status_data['status']}")

            # 4. Clean up / delete post
            del_res = await client.post("/connector/v1/discourse/delete", json={
                "platform_post_id": pub_data["platform_post_id"],
                "connection": destination_payload["connection"],
            })
            assert del_res.status_code == 200
            assert del_res.json()["deleted"] is True
            print(f"[CATALOGUE PROOF] Post deleted successfully from Forum #42. Cleanup verified.")

    finally:
        discourse_conn._http_client = original_client
        posts_store.clear()
