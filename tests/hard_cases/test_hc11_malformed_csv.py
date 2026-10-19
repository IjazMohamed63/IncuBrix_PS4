import pytest
from engine.catalogue_importer import catalogue_importer


def test_hc11_malformed_csv_rows_isolation_and_error_report():
    """HC11: CSV import contains malformed URLs, missing required fields, syntax errors.

    Expected: Validation isolates invalid rows, continues processing valid rows,
    generates downloadable row-by-row error report.
    """
    csv_content = """name,url,platform_key,connector_key
Valid Destination,https://discourse.example.com/c/general,discourse,discourse
,https://discourse.example.com/c/missing-name,discourse,discourse
Invalid URL Entry,ftp://not_a_valid_http_address,discourse,discourse
Missing Platform Key,https://discourse.example.com/c/no-platform,,discourse
Second Valid Destination,https://dev.to,devto,devto
"""

    result = catalogue_importer.import_csv_content(csv_content)

    assert result.total_rows == 5
    # 2 valid rows imported
    assert result.imported_rows == 2
    # 3 invalid rows isolated
    assert result.invalid_rows == 3

    # Generate downloadable row-by-row CSV error report
    error_csv = catalogue_importer.generate_error_report_csv(result)
    assert "row_number,field,error_message,raw_data" in error_csv
    assert "Missing required fields" in error_csv
    assert "Malformed URL" in error_csv

    # Verify valid destinations were still imported successfully
    names = [d["name"] for d in result.destinations]
    assert "Valid Destination" in names
    assert "Second Valid Destination" in names

    print(f"\n[HC11 PASS] Malformed rows successfully isolated ({result.invalid_rows} invalid, {result.imported_rows} valid). Downloadable error report verified.")
