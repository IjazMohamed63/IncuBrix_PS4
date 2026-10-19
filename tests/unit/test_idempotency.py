import asyncio
import pytest
from unittest.mock import AsyncMock
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, PublishResponse, Rendition
from core.errors import IncuBrixError
from core.idempotency import idempotency_manager
from engine.publisher import PublishEngine


@pytest.fixture(autouse=True)
def clean_idempotency():
    idempotency_manager.clear()
    yield
    idempotency_manager.clear()


@pytest.mark.asyncio
async def test_idempotency_same_key_same_body_returns_same_result():
    """Verify same key + same body returns the same result without re-publishing."""
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest)
    connector.publish = AsyncMock(
        return_value=PublishResponse(
            platform_post_id="post_idemp_101",
            live_url="http://test/posts/101",
            status="published",
        )
    )
    publisher = PublishEngine()

    rendition = Rendition(title="Identical Title", body="Identical Body Content")
    destination = DestinationPayload(
        id="dest_idemp_01",
        name="Forum",
        platform_key="discourse",
        parameters={"base_url": "http://test"},
    )
    connection = ConnectionPayload(base_url="http://test")
    key = "idemp_test_same_key_001"

    # First execution
    res1 = await publisher.publish(rendition, destination, connection, key, connector_override=connector)
    assert res1["platform_post_id"] == "post_idemp_101"
    assert connector.publish.call_count == 1

    # Second execution with identical payload and key
    res2 = await publisher.publish(rendition, destination, connection, key, connector_override=connector)
    assert res2["platform_post_id"] == "post_idemp_101"
    # Connector publish should NOT be called a second time!
    assert connector.publish.call_count == 1


@pytest.mark.asyncio
async def test_idempotency_same_key_different_body_returns_conflict_409():
    """Verify same key + different body returns 409 Conflict."""
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest)
    connector.publish = AsyncMock(
        return_value=PublishResponse(
            platform_post_id="post_first",
            live_url="http://test/posts/1",
            status="published",
        )
    )
    publisher = PublishEngine()

    destination = DestinationPayload(id="dest_01", platform_key="discourse", parameters={"base_url": "http://test"})
    connection = ConnectionPayload(base_url="http://test")
    key = "idemp_collision_test_key"

    # First request
    rendition1 = Rendition(title="First Version", body="First body")
    await publisher.publish(rendition1, destination, connection, key, connector_override=connector)

    # Second request with identical key but DIFFERENT body
    rendition2 = Rendition(title="Different Modified Title", body="Completely different body")
    with pytest.raises(IncuBrixError) as exc_info:
        await publisher.publish(rendition2, destination, connection, key, connector_override=connector)

    err = exc_info.value
    assert err.status_code == 409
    assert "already used with a different request payload" in err.message


@pytest.mark.asyncio
async def test_idempotency_parallel_concurrency_creates_exactly_one_post():
    """Concurrency test: parallel simultaneous requests with same key must create exactly ONE post."""
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest)

    call_counter = 0

    async def delayed_publish(*args, **kwargs):
        nonlocal call_counter
        call_counter += 1
        # Simulate slight network delay
        await asyncio.sleep(0.05)
        return PublishResponse(
            platform_post_id=f"concurrent_post_{call_counter}",
            live_url=f"http://test/posts/{call_counter}",
            status="published",
        )

    connector.publish = AsyncMock(side_effect=delayed_publish)
    publisher = PublishEngine()

    rendition = Rendition(title="Concurrent Title", body="Concurrent Body")
    destination = DestinationPayload(id="dest_concurrent", platform_key="discourse", parameters={"base_url": "http://test"})
    connection = ConnectionPayload(base_url="http://test")
    key = "idemp_concurrent_key_parallel_999"

    # Fire 5 concurrent requests simultaneously
    tasks = [
        publisher.publish(rendition, destination, connection, key, connector_override=connector)
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)

    # All 5 results must have the exact same post ID
    assert len(results) == 5
    first_post_id = results[0]["platform_post_id"]
    for r in results:
        assert r["platform_post_id"] == first_post_id

    # The underlying connector must have been called EXACTLY ONCE!
    assert connector.publish.call_count == 1
    assert call_counter == 1
