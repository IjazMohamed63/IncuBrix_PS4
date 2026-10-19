import pytest
from engine.catalogue_importer import catalogue_importer


def test_hc12_mixed_languages_preservation_and_detection():
    """HC12: CSV import contains mixed languages across global communities.

    Expected: Ingestion preserves language metadata; content tailoring engine flags
    language mismatches or triggers localized renditions.
    """
    csv_content = """name,url,platform_key,connector_key,language,geo
English Developer Forum,https://forum.en.example.com,discourse,discourse,en,US
German Tech Hub,https://forum.de.example.com,discourse,discourse,de,DE
Japanese AI Community,https://forum.jp.example.com,discourse,discourse,ja,JP
Spanish Founders Network,https://forum.es.example.com,discourse,discourse,es,ES
French Indie Blog,https://blog.fr.example.com,ghost,ghost,fr,FR
"""

    result = catalogue_importer.import_csv_content(csv_content)

    assert result.total_rows == 5
    assert result.imported_rows == 5
    assert result.invalid_rows == 0

    # Verify language detection list contains all distinct languages
    expected_langs = ["de", "en", "es", "fr", "ja"]
    assert result.languages_detected == expected_langs

    # Verify per-row language metadata is preserved on each destination
    dest_lang_map = {d["name"]: d["language"] for d in result.destinations}
    assert dest_lang_map["German Tech Hub"] == "de"
    assert dest_lang_map["Japanese AI Community"] == "ja"
    assert dest_lang_map["Spanish Founders Network"] == "es"
    assert dest_lang_map["French Indie Blog"] == "fr"

    print(f"\n[HC12 PASS] Mixed languages successfully preserved: {result.languages_detected}")
