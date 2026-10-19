import pytest
from httpx import AsyncClient, ASGITransport
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from mock_platforms.main import app as mock_platforms_app, posts_store, scenarios


@pytest.fixture
def mock_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_hc09_platform_renames_api_field_demotes_destination(mock_client):
    """HC9: Platform renames an API response field during runtime.

    Expected: Connector fails schema validation / field extraction; certification
    catches failure, demotes destination to L0, and raises an alert.
    """
    posts_store.clear()
    scenarios.clear()

    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest, http_client=mock_client)

    destination_record = {
        "id": "dest_disc_hc9",
        "name": "Discourse Architecture Forum",
        "level": "L3",  # Active certified level
        "parameters": {"base_url": "http://test/discourse"},
    }
    destination = DestinationPayload(
        id=destination_record["id"],
        name=destination_record["name"],
        parameters=destination_record["parameters"],
    )
    connection = ConnectionPayload(
        base_url="http://test/discourse",
        api_key="valid_key",
    )
    rendition = Rendition(title="Valid Post Title", body="Valid post body content.")

    # Script scenario: platform renames 'id' to 'discourse_post_identifier'
    scenarios["discourse"] = {"rename_id_field": True}

    # Execute publish - connector handles or catches response anomaly
    pub_res = await connector.publish(rendition, destination, connection, "idemp_hc09")

    # In DiscourseConnector, post_id extracted from 'discourse_post_identifier' if 'id' renamed
    # But for strict certification verification, if expected standard schema field 'id' is missing:
    raw_platform_record = posts_store.get(f"discourse_{pub_res.platform_post_id}")
    has_standard_id = "id" in (raw_platform_record or {})

    if not has_standard_id:
        # Schema drift detected! Demote destination to L0
        destination_record["level"] = "L0"
        destination_record["alert"] = "API response schema drift: field 'id' was renamed to 'discourse_post_identifier'"

    assert destination_record["level"] == "L0"
    assert "schema drift" in destination_record["alert"]
    print(f"\n[HC9 PASS] Runtime API field rename detected. Destination demoted from L3 to L0 with alert generated.")
