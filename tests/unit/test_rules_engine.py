import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError
from engine.publisher import PublishEngine
from engine.rules_engine import PostingRulesEngine, RuleAction, audit_store


@pytest.fixture
def rules_engine() -> PostingRulesEngine:
    audit_store.clear()
    return PostingRulesEngine(store=audit_store)


def test_rules_engine_allows_valid_content(rules_engine):
    rendition = Rendition(title="Clean Title", body="Quality discussion body without forbidden elements.")
    destination = DestinationPayload(
        id="dest_clean",
        name="Tech Forum",
        parameters={
            "frequency_cap": 24,
            "self_promo_allowed": True,
            "link_policy": "allowed",
            "disclosure_required": False,
        },
    )
    decision = rules_engine.evaluate(rendition, destination)
    assert decision.action == RuleAction.ALLOW
    assert decision.rule is None


def test_link_policy_none_blocks_content_with_links(rules_engine):
    rendition = Rendition(
        title="Check this out",
        body="Read our blog post at https://example.com/post for more info.",
    )
    destination = DestinationPayload(
        id="dest_no_links",
        name="No Links Community",
        parameters={"link_policy": "none"},
    )
    decision = rules_engine.evaluate(rendition, destination)
    assert decision.action == RuleAction.BLOCK
    assert decision.rule == "link_policy"
    assert "strictly forbids external links" in decision.reason


def test_link_policy_whitelist_enforcement(rules_engine):
    rendition = Rendition(
        title="Reference Post",
        body="Reference link: https://unapproved-domain.org/article",
    )
    destination = DestinationPayload(
        id="dest_whitelist",
        name="Whitelisted Links Only",
        parameters={"link_policy": "whitelist", "allowed_domains": ["trusted.org", "wikipedia.org"]},
    )
    decision = rules_engine.evaluate(rendition, destination)
    assert decision.action == RuleAction.BLOCK
    assert decision.rule == "link_policy"
    assert "domain whitelist" in decision.reason


def test_automation_not_allowed_blocks_bot_publish(rules_engine):
    rendition = Rendition(title="Bot Post", body="Automated content.")
    destination = DestinationPayload(
        id="dest_manual_only",
        name="High Trust Human Only",
        parameters={"automation_allowed": False},
    )
    decision = rules_engine.evaluate(rendition, destination)
    assert decision.action == RuleAction.BLOCK
    assert decision.rule == "automation_permission"
    assert "assisted" in decision.required_human_action.lower()


@pytest.mark.asyncio
async def test_blocked_post_provably_never_reaches_connector():
    """Verify that a blocked post provably never reaches connector using a spy mock."""
    audit_store.clear()
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest)
    connector.publish = AsyncMock()

    publisher = PublishEngine()

    # Create content that violates self_promo rule
    rendition = Rendition(title="Buy now sale!", body="Get discount now.", custom_fields={"is_promotional": True})
    destination = DestinationPayload(
        id="dest_spy_check",
        name="Strict Forum",
        platform_key="discourse",
        parameters={"self_promo_allowed": False},
    )
    connection = ConnectionPayload(base_url="http://test", api_key="k")

    with pytest.raises(IncuBrixError) as exc_info:
        await publisher.publish(
            rendition=rendition,
            destination=destination,
            connection=connection,
            idempotency_key="idemp_spy_test",
            connector_override=connector,
        )

    # Assert error was raised
    assert exc_info.value.code == ErrorCode.PLATFORM_CONTENT_REJECTED
    # Assert spy was called exactly 0 times!
    assert connector.publish.call_count == 0
