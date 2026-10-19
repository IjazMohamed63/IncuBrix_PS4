import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

# Configurable domain keyword dictionaries for the 6 core verticals
VERTICAL_KEYWORDS: Dict[str, List[str]] = {
    "ai": [
        "ai", "artificial intelligence", "machine learning", "deep learning", "llm",
        "gpt", "neural", "nlp", "computer vision", "inference", "generative ai", "data science"
    ],
    "video": [
        "video", "streaming", "encoding", "transcoding", "webrtc", "ffmpeg",
        "hls", "dash", "codec", "av1", "h264", "hevc", "mp4", "rendering", "motion"
    ],
    "marketing": [
        "marketing", "seo", "growth", "distribution", "content marketing",
        "analytics", "conversion", "copywriting", "campaign", "social media", "branding"
    ],
    "saas": [
        "saas", "b2b", "subscription", "arr", "mrr", "churn", "pricing",
        "multi-tenant", "cloud", "enterprise", "api", "software"
    ],
    "creators": [
        "creator", "influencer", "youtube", "tiktok", "podcast", "newsletter",
        "audience", "community", "patreon", "substack", "monetization"
    ],
    "founders": [
        "founder", "startup", "bootstrapping", "indie hacker", "venture capital",
        "fundraising", "pitch", "angel", "accelerator", "mvp", "entrepreneur"
    ],
}


class RelevanceResult(BaseModel):
    score: int = Field(ge=1, le=5)  # 1 to 5
    verticals_matched: List[str] = Field(default_factory=list)
    explanation: str


class RelevanceScorer:
    """Configurable and explainable relevance scoring engine (1 to 5 scale).
    
    Scores destinations based on topic alignment with target verticals:
    - AI
    - Video
    - Marketing
    - SaaS
    - Creators
    - Founders
    """

    def __init__(self, vertical_keywords: Optional[Dict[str, List[str]]] = None):
        self.keywords = vertical_keywords or VERTICAL_KEYWORDS

    def score(
        self,
        name: str,
        category: str = "",
        audience_tags: Optional[List[str]] = None,
        description: str = "",
    ) -> RelevanceResult:
        """Computes relevance score 1-5 with an explainable justification."""
        combined_text = f"{name} {category} {' '.join(audience_tags or [])} {description}".lower()

        matched_verticals: Dict[str, int] = {}
        for vertical, kws in self.keywords.items():
            matches = sum(1 for kw in kws if re.search(r'\b' + re.escape(kw) + r'\b', combined_text))
            if matches > 0:
                matched_verticals[vertical] = matches

        total_matches = sum(matched_verticals.values())
        num_verticals = len(matched_verticals)

        # Explainable rubric:
        # Score 5: Strong multi-vertical alignment (>= 4 keyword matches across >= 2 verticals)
        # Score 4: Solid domain alignment (>= 3 matches or strong single vertical >= 3)
        # Score 3: Moderate alignment (1-2 matches in relevant vertical)
        # Score 2: Weak / tangential alignment (broad category match, 1 weak match)
        # Score 1: Minimal or unrelated alignment (0 matches, generic general channel)
        if total_matches >= 4 and num_verticals >= 2:
            score = 5
            vertical_names = ", ".join(matched_verticals.keys())
            explanation = f"High relevance (score 5): Strong multi-vertical alignment across {vertical_names} with {total_matches} topical keyword matches."
        elif total_matches >= 3 or (total_matches >= 2 and num_verticals >= 2):
            score = 4
            vertical_names = ", ".join(matched_verticals.keys())
            explanation = f"High relevance (score 4): Direct match with {vertical_names} community interests ({total_matches} matches)."
        elif total_matches >= 1:
            score = 3
            vertical_names = ", ".join(matched_verticals.keys())
            explanation = f"Moderate relevance (score 3): Aligns with {vertical_names} topic space."
        elif category.lower() in ("tech", "technology", "general", "developer", "engineering"):
            score = 2
            explanation = "Low relevance (score 2): Broad category match with no direct vertical keyword matches."
        else:
            score = 1
            explanation = "Minimal relevance (score 1): Unrelated category with 0 target vertical keyword matches."

        return RelevanceResult(
            score=score,
            verticals_matched=list(matched_verticals.keys()),
            explanation=explanation,
        )


relevance_scorer = RelevanceScorer()
