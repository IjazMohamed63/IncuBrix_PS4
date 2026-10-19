import csv
import io
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from core.logging import get_logger

logger = get_logger("catalogue_importer")

REQUIRED_CSV_FIELDS = ["name", "url", "platform_key", "connector_key"]


class RowImportError(BaseModel):
    row_number: int
    data: Dict[str, Any]
    error: str
    field: Optional[str] = None


class CatalogueImportResult(BaseModel):
    total_rows: int
    imported_rows: int
    duplicate_rows: int
    invalid_rows: int
    destinations: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[RowImportError] = Field(default_factory=list)
    languages_detected: List[str] = Field(default_factory=list)


def normalize_url(url: str) -> str:
    """Normalizes URL by stripping whitespace, trailing slashes, canonicalizing scheme to https, and lowercasing domain."""
    if not url:
        return ""
    url = url.strip()
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    normalized = f"https://{netloc}{path}"
    return normalized



def is_valid_url(url: str) -> bool:
    """Validates URL format."""
    parsed = urlparse(url)
    return bool(parsed.scheme in ("http", "https") and parsed.netloc)


class CatalogueImporter:
    """Imports destination catalogue CSVs with validation, normalization, deduplication, and mixed-language handling."""

    def import_csv_content(self, csv_content: str) -> CatalogueImportResult:
        reader = csv.DictReader(io.StringIO(csv_content))
        total_rows = 0
        imported_rows = 0
        duplicate_rows = 0
        invalid_rows = 0

        destinations: List[Dict[str, Any]] = []
        errors: List[RowImportError] = []
        seen_keys: set[Tuple[str, str]] = set()  # (normalized_url, platform_key)
        languages_detected: set[str] = set()

        for idx, row in enumerate(reader, start=2):  # row 1 is header
            total_rows += 1

            # 1. Check required fields
            missing = [f for f in REQUIRED_CSV_FIELDS if not row.get(f) or not str(row[f]).strip()]
            if missing:
                invalid_rows += 1
                errors.append(
                    RowImportError(
                        row_number=idx,
                        data=row,
                        error=f"Missing required fields: {', '.join(missing)}",
                        field=missing[0],
                    )
                )
                continue

            raw_url = row["url"].strip()
            # 2. Validate URL format
            if not is_valid_url(raw_url):
                invalid_rows += 1
                errors.append(
                    RowImportError(
                        row_number=idx,
                        data=row,
                        error=f"Malformed URL '{raw_url}': must be valid http or https address",
                        field="url",
                    )
                )
                continue

            # 3. Normalize URL and check deduplication (HC10)
            platform_key = row["platform_key"].strip().lower()
            normalized = normalize_url(raw_url)
            dedup_key = (normalized, platform_key)

            if dedup_key in seen_keys:
                duplicate_rows += 1
                errors.append(
                    RowImportError(
                        row_number=idx,
                        data=row,
                        error=f"Duplicate destination: normalized URL '{normalized}' already registered for platform '{platform_key}'",
                        field="url",
                    )
                )
                continue

            seen_keys.add(dedup_key)

            # 4. Extract language and metadata (HC12: mixed languages)
            language = row.get("language", "en").strip().lower() or "en"
            languages_detected.add(language)

            destination_record = {
                "name": row["name"].strip(),
                "url": normalized,
                "platform_key": platform_key,
                "connector_key": row["connector_key"].strip().lower(),
                "surface": row.get("surface", "default").strip(),
                "category": row.get("category", "general").strip(),
                "language": language,
                "geo": row.get("geo", "global").strip(),
                "est_audience": int(row.get("est_audience", 0) or 0),
                "frequency_cap": int(row.get("frequency_cap", 24) or 24),
                "self_promo_allowed": row.get("self_promo_allowed", "true").lower() in ("true", "1", "yes"),
                "link_policy": row.get("link_policy", "allowed").strip().lower(),
                "disclosure_required": row.get("disclosure_required", "false").lower() in ("true", "1", "yes"),
                "automation_allowed": row.get("automation_allowed", "true").lower() in ("true", "1", "yes"),
            }

            destinations.append(destination_record)
            imported_rows += 1

        logger.info(
            f"Catalogue import finished: {imported_rows} valid, {duplicate_rows} duplicates, {invalid_rows} invalid from {total_rows} total rows."
        )

        return CatalogueImportResult(
            total_rows=total_rows,
            imported_rows=imported_rows,
            duplicate_rows=duplicate_rows,
            invalid_rows=invalid_rows,
            destinations=destinations,
            errors=errors,
            languages_detected=sorted(list(languages_detected)),
        )

    def generate_error_report_csv(self, result: CatalogueImportResult) -> str:
        """Constructs row-by-row downloadable CSV error report."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["row_number", "field", "error_message", "raw_data"])
        for err in result.errors:
            writer.writerow([err.row_number, err.field or "", err.error, str(err.data)])
        return output.getvalue()


catalogue_importer = CatalogueImporter()
