import pytest
from connectors.schemas import Rendition
from engine.catalogue_importer import catalogue_importer
from engine.recommender import recommender
from pathlib import Path


@pytest.fixture
def seed_destinations():
    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "seed_catalogue.csv"
    content = csv_path.read_text(encoding="utf-8")
    result = catalogue_importer.import_csv_content(content)
    # Give destinations consistent IDs
    for idx, d in enumerate(result.destinations):
        d["id"] = f"dest_{idx+1:03d}"
    return result.destinations


def test_recommender_precision_at_10(seed_destinations):
    """Verifies that the recommender achieves >= 0.80 Precision@10 on labelled AI content."""
    ai_rendition = Rendition(
        title="Scaling Generative AI Video Ingestion Pipelines",
        body="Architectural benchmark comparing multimodal LLM inference latencies and GPU clusters.",
        tags=["ai", "video", "machine-learning", "deep-learning", "streaming"],
        canonical_url="https://incubrix.com/blog/generative-video",
    )

    # Ground truth: destinations in seed catalogue relevant to AI or Video
    ground_truth_relevant_ids = set()
    for d in seed_destinations:
        cat = d.get("category", "").lower()
        tags = set(d.get("audience_tags", []))
        if cat in ("ai", "video") or any(t in ("ai", "video", "machine-learning") for t in tags):
            ground_truth_relevant_ids.add(d["id"])

    # Run recommendation
    top_10 = recommender.recommend(ai_rendition, seed_destinations, top_k=10)
    assert len(top_10) == 10

    # Compute Precision@10
    precision = recommender.evaluate_precision_at_k(top_10, ground_truth_relevant_ids, k=10)
    print(f"\n[RECOMMENDER EVAL] Evaluated Precision@10: {precision:.2%}")
    for idx, rec in enumerate(top_10, 1):
        is_relevant = rec.destination_id in ground_truth_relevant_ids
        print(f"  #{idx} {rec.name} (Score: {rec.score}) - Relevant: {is_relevant}")

    assert precision >= 0.80, f"Expected Precision@10 >= 80%, got {precision:.2%}"


def test_recommender_excludes_demoted_l0_destinations(seed_destinations):
    """Verifies that L0 demoted destinations are strictly excluded from recommendations."""
    # Demote the top destination to L0
    seed_destinations[0]["level"] = "L0"
    demoted_id = seed_destinations[0]["id"]

    rendition = Rendition(
        title="OpenAI API Integration Guide",
        body="Detailed guide for developers building on OpenAI models.",
        tags=["ai", "openai", "api"],
    )

    top_recs = recommender.recommend(rendition, seed_destinations, top_k=10)
    rec_ids = [r.destination_id for r in top_recs]
    assert demoted_id not in rec_ids, "L0 demoted destination must be excluded from recommendations"
