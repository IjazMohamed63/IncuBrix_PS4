import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from connectors.schemas import Rendition
from engine.relevance_scorer import relevance_scorer


class RecommendedDestination(BaseModel):
    destination_id: str
    name: str
    platform_key: str
    surface: str
    score: float
    reasons: List[str] = Field(default_factory=list)


class DestinationRecommender:
    """Smart destination recommendation engine evaluating topical relevance,
    surface alignment, and policy compatibility.
    """

    def recommend(
        self,
        rendition: Rendition,
        destinations: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[RecommendedDestination]:
        """Ranks destinations for a given rendition and returns top_k recommendations."""
        scored: List[RecommendedDestination] = []

        combined_text = f"{rendition.title} {rendition.body} {' '.join(rendition.tags)}".lower()
        rendition_tags = set(t.lower() for t in rendition.tags)
        has_links = bool(rendition.canonical_url or "http" in combined_text)

        for dest in destinations:
            dest_id = dest.get("id") or "dest_id"
            name = dest.get("name", "")
            platform = dest.get("platform_key", "")
            surface = dest.get("surface", "default")
            category = dest.get("category", "").lower()
            dest_tags = set(t.lower() for t in dest.get("audience_tags", []))
            params = dest.get("parameters", {})

            # 1. Hard filters
            if dest.get("level") == "L0" or params.get("excluded_from_recommendations"):
                continue

            link_policy = dest.get("link_policy", params.get("link_policy", "allowed")).lower()
            if has_links and link_policy == "none":
                continue

            score = 10.0
            reasons = []

            # 2. Tag overlap
            tag_overlap = rendition_tags.intersection(dest_tags)
            if tag_overlap:
                score += len(tag_overlap) * 15.0
                reasons.append(f"Tag alignment: {', '.join(tag_overlap)}")

            # 3. Category match
            if category in combined_text:
                score += 20.0
                reasons.append(f"Category '{category}' directly matches content")

            # 4. Vertical relevance scoring (AI, video, marketing, SaaS, creators, founders)
            rel_res = relevance_scorer.score(name, category, list(dest_tags), description=name)
            score += rel_res.score * 8.0
            if rel_res.verticals_matched:
                reasons.append(f"Vertical match: {', '.join(rel_res.verticals_matched)}")

            # 5. Audience reach factor (small boost for established destinations)
            est_audience = dest.get("est_audience", 0)
            if est_audience > 10000:
                score += 5.0
                reasons.append(f"Established audience ({est_audience:,})")

            scored.append(
                RecommendedDestination(
                    destination_id=dest_id,
                    name=name,
                    platform_key=platform,
                    surface=surface,
                    score=round(score, 2),
                    reasons=reasons,
                )
            )

        # Sort descending by score
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def evaluate_precision_at_k(
        self,
        recommendations: List[RecommendedDestination],
        ground_truth_relevant_ids: set[str],
        k: int = 10,
    ) -> float:
        """Calculates Precision@K against a labelled ground-truth set."""
        if not recommendations or k <= 0:
            return 0.0

        top_k = recommendations[:k]
        relevant_in_top_k = sum(1 for rec in top_k if rec.destination_id in ground_truth_relevant_ids)
        return relevant_in_top_k / min(k, len(top_k))


recommender = DestinationRecommender()
