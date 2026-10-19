import pytest
from connectors.schemas import DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError
from engine.publisher import PublishEngine
from engine.rules_engine import PostingRulesEngine, RuleAction
from engine.tailoring import DEFAULT_AI_DISCLOSURE, tailoring_engine
from unittest.mock import AsyncMock


def test_hc14_ai_disclosure_enforcement_and_tailoring():
    """HC14: Destination enforces mandatory AI-content disclosure tag.

    Expected: Tailoring engine verifies presence of AI disclosure; if missing,
    appends compliant disclosure statement or flags for user confirmation.
    """
    rules_engine = PostingRulesEngine()

    destination = DestinationPayload(
        id="dest_disc_hc14",
        name="AI Strict Disclosure Community",
        platform_key="discourse",
        parameters={
            "base_url": "http://test/discourse",
            "disclosure_required": True,  # Mandatory AI disclosure rule
        },
    )

    # 1. Content without AI disclosure: Pre-flight rules engine BLOCKS publication
    unadapted_rendition = Rendition(
        title="Scaling Video AI Infrastructure",
        body="Deep dive into our model weights and quantization strategies.",
        ai_disclosure=None,  # Missing mandatory disclosure
    )

    decision = rules_engine.evaluate(unadapted_rendition, destination)
    assert decision.action == RuleAction.BLOCK
    assert decision.rule == "ai_disclosure"
    assert "mandatory" in decision.reason.lower()
    print(f"\n[HC14 PASS] Unadapted post blocked by pre-flight rule: {decision.reason}")

    # 2. Content passes through tailoring engine: automatically appends compliant disclosure statement
    tailored_rendition = tailoring_engine.tailor(unadapted_rendition, destination)
    assert tailored_rendition.ai_disclosure is not None
    assert DEFAULT_AI_DISCLOSURE in tailored_rendition.body
    assert DEFAULT_AI_DISCLOSURE == tailored_rendition.ai_disclosure

    # 3. Re-evaluate tailored content: passes pre-flight rules with flying colors!
    second_decision = rules_engine.evaluate(tailored_rendition, destination)
    assert second_decision.action == RuleAction.ALLOW
    print(f"[HC14 PASS] Tailoring engine successfully appended compliant AI disclosure: post ALLOWED.")
