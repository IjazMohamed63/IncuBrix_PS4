import pytest
from connectors.assisted.client import AssistedConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, MediaItem, Rendition
from core.errors import ErrorCode, IncuBrixError


@pytest.fixture
def assisted_connector() -> AssistedConnector:
    manifest = registry.get_manifest("assisted")
    return AssistedConnector(manifest)


@pytest.mark.asyncio
async def test_assisted_validate_success(assisted_connector):
    rendition = Rendition(
        title="High-Trust Community Discussion",
        body="Detailed discussion topic conforming to community etiquette.",
    )
    destination = DestinationPayload(name="Indie Hackers")
    connection = ConnectionPayload()

    res = await assisted_connector.validate(rendition, destination, connection)
    assert res.ok is True
    assert res.violations == []


@pytest.mark.asyncio
async def test_assisted_validate_field_level_violations(assisted_connector):
    rendition = Rendition(title="", body="")
    destination = DestinationPayload(name="Indie Hackers")
    connection = ConnectionPayload()

    res = await assisted_connector.validate(rendition, destination, connection)
    assert res.ok is False
    assert any("title" in v for v in res.violations)


@pytest.mark.asyncio
async def test_assisted_build_assist_pack(assisted_connector):
    rendition = Rendition(
        title="Manual Showcase Thread",
        body="Sharing our architecture lessons learned.",
        media=[
            MediaItem(url="http://media.local/diagram.png", media_type="image/png"),
            MediaItem(url="http://media.local/benchmark.png", media_type="image/png"),
        ],
        ai_disclosure="This draft was outlined with AI assistance.",
    )
    destination = DestinationPayload(
        name="Indie Hackers Showcase",
        url="https://community.example.com/submit",
    )

    pack = await assisted_connector.build_assist_pack(rendition, destination)
    assert len(pack.files) == 2
    assert "diagram.png" in pack.files[0]
    assert "benchmark.png" in pack.files[1]
    assert "Manual Showcase Thread" in pack.caption
    assert "[AI Disclosure: This draft was outlined with AI assistance.]" in pack.caption
    assert pack.deep_link == "https://community.example.com/submit"
    assert len(pack.checklist) >= 4
    assert any(c.id == "chk_manual_post" and c.required for c in pack.checklist)
    assert any(c.id == "chk_ai_disclosure" for c in pack.checklist)


@pytest.mark.asyncio
async def test_assisted_publish_is_never_reported_as_published(assisted_connector):
    """Crucial requirement: package creation is never reported as 'published'.

    Calling publish on assisted connector must fail with DEST_SPEC_VIOLATION.
    """
    rendition = Rendition(title="T", body="B")
    destination = DestinationPayload(name="Forum")
    connection = ConnectionPayload()

    with pytest.raises(IncuBrixError) as exc_info:
        await assisted_connector.publish(rendition, destination, connection, "k123")

    assert exc_info.value.code == ErrorCode.DEST_SPEC_VIOLATION
    assert "never reported as 'published'" in exc_info.value.message or "build_assist_pack" in exc_info.value.message
