import pytest
from engine.catalogue_importer import catalogue_importer


def test_hc10_csv_import_duplicate_detection_and_reporting():
    """HC10: CSV import contains duplicate destination entries (same URL + platform).

    Expected: Deduplication engine flags subsequent rows as duplicates, keeps primary,
    records duplicate count in import report.
    """
    csv_content = """name,url,platform_key,connector_key,category,frequency_cap
Tech Forum Alpha,https://forum.example.com/c/tech,discourse,discourse,tech,24
Tech Forum Beta Duplicate,https://forum.example.com/c/tech/,discourse,discourse,tech,24
AI Community,https://lemmy.world/c/ai,lemmy,lemmy,ai,12
AI Community Normalized Dup,http://lemmy.world/c/ai,lemmy,lemmy,ai,12
"""

    result = catalogue_importer.import_csv_content(csv_content)

    assert result.total_rows == 4
    # 2 unique destinations kept
    assert result.imported_rows == 2
    # 2 duplicate rows identified
    assert result.duplicate_rows == 2

    # Verify duplicates are recorded in errors list
    dup_errors = [e for e in result.errors if "Duplicate" in e.error]
    assert len(dup_errors) == 2

    # Verify primary destination preserved
    imported_names = [d["name"] for d in result.destinations]
    assert "Tech Forum Alpha" in imported_names
    assert "AI Community" in imported_names
    assert "Tech Forum Beta Duplicate" not in imported_names

    print(f"\n[HC10 PASS] CSV Deduplication verified: {result.duplicate_rows} duplicate rows detected and isolated.")
