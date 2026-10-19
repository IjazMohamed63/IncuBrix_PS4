import pytest
from connectors.schemas import DestinationPayload, Rendition
from engine.relevance_scorer import relevance_scorer
from engine.rule_capture import rule_capture_manager
from engine.tailoring import tailoring_engine


def test_relevance_scorer_six_verticals_and_explainable_rubric():
    """Verifies relevance scoring 1-5 across AI, video, marketing, SaaS, creators, and founders."""
    # 1. AI Vertical
    ai_res = relevance_scorer.score(
        name="Generative AI Deep Learning Lab",
        category="ai",
        audience_tags=["llm", "neural-networks", "machine-learning"],
    )
    assert ai_res.score >= 4
    assert "ai" in ai_res.verticals_matched
    assert "relevance" in ai_res.explanation.lower()

    # 2. Video Vertical
    video_res = relevance_scorer.score(
        name="WebRTC & Video Streaming Architecture",
        category="video",
        audience_tags=["ffmpeg", "hls", "transcoding"],
    )
    assert video_res.score >= 4
    assert "video" in video_res.verticals_matched

    # 3. Marketing Vertical
    mkt_res = relevance_scorer.score(
        name="SaaS Growth Marketing & SEO",
        category="marketing",
        audience_tags=["growth", "analytics", "seo"],
    )
    assert mkt_res.score >= 4
    assert "marketing" in mkt_res.verticals_matched

    # 4. Creators & Founders
    founders_res = relevance_scorer.score(
        name="Bootstrapping Founders & Indie Creators",
        category="founders",
        audience_tags=["startup", "creators", "mvp", "monetization"],
    )
    assert founders_res.score == 5
    assert "founders" in founders_res.verticals_matched
    assert "creators" in founders_res.verticals_matched

    # 5. Low / Unrelated Category
    unrelated_res = relevance_scorer.score(
        name="Local Gardening Club",
        category="gardening",
        audience_tags=["plants", "soil"],
    )
    assert unrelated_res.score == 1
    assert "minimal relevance" in unrelated_res.explanation.lower()


@pytest.mark.asyncio
async def test_ai_rule_capture_and_human_confirmation_workflow():
    """Verifies AI rule extraction proposing guidelines, requiring human confirmation before activation."""
    sample_rules_page = """
    Community Guidelines:
    1. Weekly Posting Limit: Members may only submit once a week to prevent spam.
    2. No self-promotion: Promotional claims, affiliate links, and commercial sales pitches are strictly prohibited.
    3. External Links: No external links allowed in post content.
    4. AI Content: Disclose AI assistance transparently with a mandatory tag.
    5. Formatting: Title limit 120 chars, Body max 5000 chars.
    6. No automated posting: Bot submissions will be banned immediately.
    """

    dest_params = {"level": "L2"}
    dest_id = "dest_guidelines_99"

    # Step 1: AI Adapter proposes rules (status: pending_confirmation)
    proposal = await rule_capture_manager.propose_rules(
        destination_id=dest_id,
        rules_text=sample_rules_page,
        rules_url="https://community.org/rules",
    )
    assert proposal.status == "pending_confirmation"
    assert proposal.proposed_rules.frequency_cap == 168  # 1 week in hours
    assert proposal.proposed_rules.self_promo_allowed is False
    assert proposal.proposed_rules.link_policy == "none"
    assert proposal.proposed_rules.disclosure_required is True
    assert proposal.proposed_rules.automation_allowed is False
    assert proposal.proposed_rules.title_max_chars == 120
    assert proposal.proposed_rules.body_max_chars == 5000

    # Rules are NOT yet active on destination
    assert "frequency_cap" not in dest_params

    # Step 2: Human operator confirms proposal
    confirmed = rule_capture_manager.confirm_rules(
        proposal_id=proposal.id,
        destination_parameters=dest_params,
        confirmed_by="alice_operator",
    )
    assert confirmed.status == "activated"
    assert confirmed.confirmed_by == "alice_operator"

    # Now rules are activated on destination
    assert dest_params["frequency_cap"] == 168
    assert dest_params["self_promo_allowed"] is False
    assert dest_params["link_policy"] == "none"
    assert dest_params["disclosure_required"] is True
    assert dest_params["automation_allowed"] is False
    assert dest_params["title_max_chars"] == 120


def test_content_tailoring_discussion_first_and_multilingual():
    """Verifies discussion-first forum framing, canonical URL, and UTF-8 multilingual preservation."""
    destination = DestinationPayload(
        id="dest_forum_01",
        name="Multilingual Architecture Forum",
        surface="forum",
        url="https://forum.incubrix.com/t/123",
        parameters={
            "require_canonical_url": True,
            "disclosure_required": True,
            "hashtag_style": "camelCase",
            "max_hashtags": 2,
            "title_max_chars": 60,
        },
    )

    multilingual_title = "स्केलिंग वितरित आर्किटेक्चर: Multi-Agent Systems in Production"
    rendition = Rendition(
        title=multilingual_title,
        body="Detailed discussion on decentralized video pipelines with UTF-8 support: 日本語と한국어.",
        tags=["distributed-systems", "artificial-intelligence", "cloud-native"],
    )

    tailored = tailoring_engine.tailor(rendition, destination)

    # 1. Discussion-first prompt appended
    assert "Discussion:" in tailored.body
    # 2. Canonical URL set
    assert tailored.canonical_url == "https://forum.incubrix.com/t/123"
    # 3. AI Disclosure appended
    assert "AI Disclosure" in tailored.body
    # 4. Hashtag style: camelCase and limited to 2
    assert len(tailored.tags) == 2
    assert tailored.tags[0] == "DistributedSystems"
    # 5. Multilingual Unicode preserved without mangling
    assert "स्केलिंग" in tailored.title
    assert "日本語" in tailored.body
    # 6. Title truncated at word boundary
    assert len(tailored.title) <= 60
    assert tailored.title.endswith("...")
