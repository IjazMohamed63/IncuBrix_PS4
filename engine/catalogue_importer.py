import csv
import io
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from core.logging import get_logger
from core.ssrf import is_ip_allowed, validate_url_ssrf_safe
from core.storage import storage_service
from engine.relevance_scorer import relevance_scorer

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
    error_report_download_url: Optional[str] = None


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
    """Imports destination catalogue CSVs with validation, normalization, deduplication, safe reachability, and enrichment."""

    def import_csv_content(
        self,
        csv_content: str,
        safe_reachability_check: bool = False,
        enrich_relevance: bool = True,
        job_id: Optional[str] = None,
    ) -> CatalogueImportResult:
        from core.jobs import job_manager

        reader = list(csv.DictReader(io.StringIO(csv_content)))
        total_rows = len(reader)
        imported_rows = 0
        duplicate_rows = 0
        invalid_rows = 0

        destinations: List[Dict[str, Any]] = []
        errors: List[RowImportError] = []
        seen_keys: set[Tuple[str, str]] = set()  # (normalized_url, platform_key)
        languages_detected: set[str] = set()

        if job_id:
            job_manager.update_progress(job_id, 10, "running")

        for idx, row in enumerate(reader, start=2):  # row 1 is header
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

            # 3. Safe reachability check (SSRF validation)
            if safe_reachability_check:
                try:
                    validate_url_ssrf_safe(raw_url)
                except Exception as ssrf_err:
                    invalid_rows += 1
                    errors.append(
                        RowImportError(
                            row_number=idx,
                            data=row,
                            error=f"Safe reachability check failed (SSRF violation): {str(ssrf_err)}",
                            field="url",
                        )
                    )
                    continue

            # 4. Normalize URL and check deduplication (HC10)
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

            # 5. Extract language and metadata (HC12: mixed languages)
            language = row.get("language", "en").strip().lower() or "en"
            languages_detected.add(language)

            name = row["name"].strip()
            category = row.get("category", "general").strip()
            tags_raw = row.get("audience_tags", "")
            audience_tags = [t.strip() for t in tags_raw.split(";") if t.strip()] if tags_raw else []

            # 6. Enrichment (Relevance scoring 1-5 with short explanation)
            relevance_score = 3
            relevance_reason = "Default moderate relevance."
            if enrich_relevance:
                rel_res = relevance_scorer.score(name, category, audience_tags)
                relevance_score = rel_res.score
                relevance_reason = rel_res.explanation

            destination_record = {
                "name": name,
                "url": normalized,
                "platform_key": platform_key,
                "connector_key": row["connector_key"].strip().lower(),
                "surface": row.get("surface", "default").strip(),
                "category": category,
                "audience_tags": audience_tags,
                "language": language,
                "geo": row.get("geo", "global").strip(),
                "est_audience": int(row.get("est_audience", 0) or 0),
                "frequency_cap": int(row.get("frequency_cap", 24) or 24),
                "self_promo_allowed": row.get("self_promo_allowed", "true").lower() in ("true", "1", "yes"),
                "link_policy": row.get("link_policy", "allowed").strip().lower(),
                "disclosure_required": row.get("disclosure_required", "false").lower() in ("true", "1", "yes"),
                "automation_allowed": row.get("automation_allowed", "true").lower() in ("true", "1", "yes"),
                "relevance_score": relevance_score,
                "relevance_reason": relevance_reason,
            }

            destinations.append(destination_record)
            imported_rows += 1

            # Progress tracking via job
            if job_id and idx % 200 == 0:
                pct = int(10 + (idx / total_rows) * 75)
                job_manager.update_progress(job_id, pct, "running")

        # 7. Generate downloadable error report CSV if errors exist
        result = CatalogueImportResult(
            total_rows=total_rows,
            imported_rows=imported_rows,
            duplicate_rows=duplicate_rows,
            invalid_rows=invalid_rows,
            destinations=destinations,
            errors=errors,
            languages_detected=sorted(list(languages_detected)),
        )

        if errors:
            err_csv = self.generate_error_report_csv(result)
            stored_report = storage_service.store_file(
                data=err_csv.encode("utf-8"),
                filename="catalogue_import_error_report.csv",
                content_type="text/csv",
            )
            result.error_report_download_url = stored_report["download_url"]

        if job_id:
            job_manager.update_progress(job_id, 100, "succeeded")

        logger.info(
            f"Catalogue import finished: {imported_rows} valid, {duplicate_rows} duplicates, {invalid_rows} invalid from {total_rows} total rows."
        )
        return result

    def generate_error_report_csv(self, result: CatalogueImportResult) -> str:
        """Constructs row-by-row downloadable CSV error report."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["row_number", "field", "error_message", "raw_data"])
        for err in result.errors:
            writer.writerow([err.row_number, err.field or "", err.error, str(err.data)])
        return output.getvalue()


catalogue_importer = CatalogueImporter()
