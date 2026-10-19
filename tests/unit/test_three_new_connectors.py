import pytest
from httpx import AsyncClient, ASGITransport

from connectors.hashnode.client import HashnodeConnector
from connectors.mrss_feed.client import MRSSFeedConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from connectors.slack.client import SlackConnector
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


@pytest.mark.asyncio
async def test_hashnode_connector_lifecycle(mock_client):
    """Verifies Hashnode GraphQL connector: validate -> publish -> get_status -> delete -> metrics."""
    manifest = registry.get_manifest("hashnode")
    connector = HashnodeConnector(manifest, http_client=mock_client)

    destination = DestinationPayload(
        id="dest_hn_01",
        name="Hashnode Tech Blog",
        platform_key="hashnode",
        parameters={"base_url": "http://test/hashnode/graphql", "publication_id": "pub_123"},
    )
    connection = ConnectionPayload(
        base_url="http://test/hashnode/graphql",
        token="hn_test_token_999",
    )
    rendition = Rendition(
        title="Building Distributed Microservices on Kubernetes",
        body="## In-Depth Architectural Guide\n\nHow to scale event-driven pipelines across clusters.",
        tags=["kubernetes", "docker", "python"],
        canonical_url="https://incubrix.com/blog/k8s",
    )

    # 1. Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True

    # 2. Publish
    pub = await connector.publish(rendition, destination, connection, "idemp_hn_01")
    assert pub.status == "published"
    assert pub.platform_post_id != ""
    assert "hashnode.com" in pub.live_url

    # 3. Get Status
    status_res = await connector.get_status(pub.platform_post_id, connection)
    assert status_res.status == "active"

    # 4. Metrics (Rule: unavailable is null, never 0)
    metrics = await connector.fetch_metrics(pub.platform_post_id, connection)
    assert metrics.views == 142
    assert metrics.shares is None  # Must be null / None, never 0!

    # 5. Delete
    del_res = await connector.delete(pub.platform_post_id, connection)
    assert del_res.deleted is True


@pytest.mark.asyncio
async def test_slack_connector_lifecycle(mock_client):
    """Verifies Slack webhook syndication connector: validate -> publish -> get_status -> delete."""
    manifest = registry.get_manifest("slack")
    connector = SlackConnector(manifest, http_client=mock_client)

    destination = DestinationPayload(
        id="dest_slack_01",
        name="Team Announcements Channel",
        platform_key="slack",
        url="http://test/slack/webhook",
        parameters={"webhook_url": "http://test/slack/webhook"},
    )
    connection = ConnectionPayload(
        base_url="http://test/slack/webhook",
        auth_type="none",
    )
    rendition = Rendition(
        title="IncuBrix 2.0 Deployment Complete",
        body="The distributed connector harness and rules engine have been deployed to production.",
        canonical_url="https://incubrix.com/changelog/2.0",
    )

    # 1. Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True

    # 2. Publish
    pub = await connector.publish(rendition, destination, connection, "idemp_slack_01")
    assert pub.status == "published"
    assert pub.platform_post_id.startswith("slack_msg_")

    # 3. Get Status
    status_res = await connector.get_status(pub.platform_post_id, connection)
    assert status_res.status == "active"

    # 4. Delete
    del_res = await connector.delete(pub.platform_post_id, connection)
    assert del_res.deleted is True


@pytest.mark.asyncio
async def test_mrss_feed_connector_lifecycle():
    """Verifies MRSS Feed XML connector: validate -> publish -> get_status -> delete."""
    manifest = registry.get_manifest("mrss_feed")
    connector = MRSSFeedConnector(manifest)

    destination = DestinationPayload(
        id="dest_mrss_01",
        name="Syndication MRSS Feed",
        platform_key="mrss_feed",
        url="https://syndication.incubrix.com/feeds/rss.xml",
    )
    connection = ConnectionPayload(auth_type="none")
    rendition = Rendition(
        title="Weekly Technical Digest: Video Transcoding",
        body="Detailed discussion on AV1 hardware encoders and latency benchmarks.",
        canonical_url="https://incubrix.com/blog/av1-benchmarks",
    )

    # 1. Validate
    val = await connector.validate(rendition, destination, connection)
    assert val.ok is True

    # 2. Publish (Generates XML item)
    pub = await connector.publish(rendition, destination, connection, "idemp_mrss_01")
    assert pub.status == "published"
    assert pub.platform_post_id.startswith("urn:uuid:")
    assert "rss.xml#" in pub.live_url

    # 3. Get Status
    status_res = await connector.get_status(pub.platform_post_id, connection)
    assert status_res.status == "active"

    # 4. Delete
    del_res = await connector.delete(pub.platform_post_id, connection)
    assert del_res.deleted is True
