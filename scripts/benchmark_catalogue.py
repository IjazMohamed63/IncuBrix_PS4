#!/usr/bin/env python3
"""Benchmarks Destination Catalogue CSV Import on 1,000 rows and records real measured time.

Requirement:
"Benchmark 1,000 rows and record the real time; do not claim under 5 minutes until measured."
"""

import io
from pathlib import Path
import sys
import time
import uuid

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from engine.catalogue_importer import catalogue_importer

LANGUAGES = ["en", "es", "hi", "ja", "ar", "fr", "de"]
PLATFORMS = ["discourse", "lemmy", "devto", "ghost", "signed_webhook", "hashnode", "slack", "mrss_feed"]
CATEGORIES = ["ai", "video", "marketing", "saas", "creators", "founders", "developer", "general"]


def generate_benchmark_csv(num_rows: int = 1000) -> str:
    """Generates 1,000 realistic rows with duplicates, mixed languages, and edge cases."""
    output = io.StringIO()
    output.write("name,url,platform_key,connector_key,surface,category,audience_tags,language,geo,est_audience,frequency_cap,self_promo_allowed,link_policy,disclosure_required,automation_allowed\n")

    for i in range(1, num_rows + 1):
        # Introduce deliberate duplicates every 50 rows
        if i % 50 == 0:
            target_id = i - 1
            url = f"https://community-{target_id}.org/forum"
        else:
            url = f"https://community-{i}.org/forum"

        # Introduce a few malformed rows (every 250 rows)
        if i % 250 == 0:
            url = f"htp:/invalid-url-domain-{i}"

        lang = LANGUAGES[i % len(LANGUAGES)]
        platform = PLATFORMS[i % len(PLATFORMS)]
        category = CATEGORIES[i % len(CATEGORIES)]
        name = f"Community Hub {i} ({category.upper()})"
        tags = f"{category};tech;distribution"

        output.write(
            f'"{name}","{url}","{platform}","{platform}","article","{category}","{tags}","{lang}","global",15000,24,true,allowed,false,true\n'
        )

    return output.getvalue()


def run_benchmark():
    print("=" * 70)
    print("IncuBrix Destination Catalogue Import Benchmark: 1,000 Rows")
    print("=" * 70)

    print("\n1. Generating 1,000 synthetic catalogue rows...")
    t_gen_start = time.perf_counter()
    csv_data = generate_benchmark_csv(1000)
    t_gen_end = time.perf_counter()
    print(f"Generated 1,000 rows in {(t_gen_end - t_gen_start)*1000:.2f}ms (size: {len(csv_data)/1024:.1f} KB)")

    print("\n2. Executing CatalogueImporter.import_csv_content with normalization, deduplication, and relevance scoring...")
    t_start = time.perf_counter()
    result = catalogue_importer.import_csv_content(csv_data, enrich_relevance=True)
    t_end = time.perf_counter()

    duration_sec = t_end - t_start
    duration_ms = duration_sec * 1000
    rows_per_sec = result.total_rows / duration_sec if duration_sec > 0 else 0

    print("\n3. Benchmark Results:")
    print(f" - Total Rows Processed : {result.total_rows:,}")
    print(f" - Valid Imported Rows  : {result.imported_rows:,}")
    print(f" - Duplicates Detected  : {result.duplicate_rows:,}")
    print(f" - Invalid/Malformed    : {result.invalid_rows:,}")
    print(f" - Languages Detected   : {', '.join(result.languages_detected)}")
    print(f" - Real Measured Time   : {duration_sec:.4f} seconds ({duration_ms:.2f} ms)")
    print(f" - Throughput Rate      : {rows_per_sec:,.1f} rows/second")
    print(f" - Under 5 Minutes Spec : {'YES (PASSED)' if duration_sec < 300 else 'NO (FAILED)'}")
    print("=" * 70)

    return result, duration_sec


if __name__ == "__main__":
    run_benchmark()
