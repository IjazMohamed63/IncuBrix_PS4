import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from connectors.registry import ConnectorRegistry, registry
from connectors.schemas import (
    ConnectionPayload,
    DestinationPayload,
    PublishResponse,
    Rendition,
)
from core.errors import ErrorCode, IncuBrixError

router = APIRouter(prefix="/api/v1/destinations", tags=["destinations"])

# In-memory catalogue store for fast runtime access and zero-dependency testability
_catalogue_store: Dict[str, Dict[str, Any]] = {}


def seed_initial_catalogue_if_empty():
    """Auto-seeds destination catalogue with initial seed data if store is empty."""
    if not _catalogue_store:
        from pathlib import Path
        seed_path = Path(__file__).resolve().parent.parent.parent / "data" / "seed_catalogue.csv"
        if seed_path.exists():
            from engine.catalogue_importer import catalogue_importer
            with open(seed_path, "r", encoding="utf-8") as f:
                content = f.read()
            res = catalogue_importer.import_csv_content(content, safe_reachability_check=False, enrich_relevance=False)
            for d in res.destinations:
                dest_id = f"dest_{uuid.uuid4().hex[:8]}"
                d["id"] = dest_id
                d["level"] = "L1" if d.get("connector_key") != "assisted" else "L0"
                d["created_at"] = datetime.now(timezone.utc).isoformat()
                _catalogue_store[dest_id] = d


seed_initial_catalogue_if_empty()



class DestinationCreateRequest(BaseModel):
    name: str
    url: str
    platform_key: str
    connector_key: str
    surface: str = "default"
    category: str = "general"
    audience_tags: List[str] = Field(default_factory=list)
    language: str = "en"
    geo: str = "global"
    est_audience: int = 0
    rules_url: Optional[str] = None
    frequency_cap: int = 24
    self_promo_allowed: bool = True
    link_policy: str = "allowed"
    disclosure_required: bool = False
    automation_allowed: bool = True
    relevance_score: int = 3
    relevance_reason: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    connection: Optional[ConnectionPayload] = None


class DestinationPublishRequest(BaseModel):
    rendition: Rendition
    idempotency_key: str


def get_registry() -> ConnectorRegistry:
    return registry


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_destination(
    payload: DestinationCreateRequest,
    reg: ConnectorRegistry = Depends(get_registry),
) -> Dict[str, Any]:
    """Adds a new destination catalogue row with zero code changes.

    Supports multi-instance scaling via configuration alone.
    """
    # Verify connector exists in registry
    _ = reg.get_connector(payload.connector_key)

    dest_id = str(uuid.uuid4())
    record = {
        "id": dest_id,
        "name": payload.name,
        "url": payload.url,
        "platform_key": payload.platform_key,
        "connector_key": payload.connector_key,
        "surface": payload.surface,
        "category": payload.category,
        "audience_tags": payload.audience_tags,
        "language": payload.language,
        "geo": payload.geo,
        "est_audience": payload.est_audience,
        "rules_url": payload.rules_url,
        "frequency_cap": payload.frequency_cap,
        "self_promo_allowed": payload.self_promo_allowed,
        "link_policy": payload.link_policy,
        "disclosure_required": payload.disclosure_required,
        "automation_allowed": payload.automation_allowed,
        "relevance_score": payload.relevance_score,
        "relevance_reason": payload.relevance_reason,
        "parameters": payload.parameters,
        "connection": payload.connection.model_dump() if payload.connection else {},
        "level": "L0",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _catalogue_store[dest_id] = record
    return record


@router.get("")
async def list_destinations() -> List[Dict[str, Any]]:
    """Lists all configured destination catalogue rows."""
    return list(_catalogue_store.values())


@router.get("/{destination_id}")
async def get_destination(destination_id: str = Path(...)) -> Dict[str, Any]:
    """Retrieves destination catalogue row by ID."""
    record = _catalogue_store.get(destination_id)
    if not record:
        raise IncuBrixError(
            code=ErrorCode.NOT_FOUND,
            message=f"Destination '{destination_id}' not found in catalogue.",
            status_code=404,
        )
    return record


@router.post("/{destination_id}/publish")
async def publish_to_destination(
    destination_id: str = Path(...),
    req: DestinationPublishRequest = Body(...),
    reg: ConnectorRegistry = Depends(get_registry),
) -> Dict[str, Any]:
    """Publishes content to a specific catalogue destination row.

    Directly invokes the associated connector without any code changes.
    """
    dest = _catalogue_store.get(destination_id)
    if not dest:
        raise IncuBrixError(
            code=ErrorCode.NOT_FOUND,
            message=f"Destination '{destination_id}' not found in catalogue.",
            status_code=404,
        )

    connector = reg.get_connector(dest["connector_key"])
    dest_payload = DestinationPayload(
        id=dest["id"],
        name=dest["name"],
        url=dest["url"],
        platform_key=dest["platform_key"],
        surface=dest["surface"],
        parameters=dest.get("parameters", {}),
    )
    conn_dict = dest.get("connection") or {}
    conn_payload = ConnectionPayload.model_validate(conn_dict)

    res: PublishResponse = await connector.publish(
        rendition=req.rendition,
        destination=dest_payload,
        connection=conn_payload,
        idempotency_key=req.idempotency_key,
    )
    return res.model_dump()


class RuleProposeRequest(BaseModel):
    rules_text: str
    rules_url: Optional[str] = None


class RuleConfirmRequest(BaseModel):
    proposal_id: str
    confirmed_by: Optional[str] = "human_operator"


@router.post("/import-csv", status_code=status.HTTP_202_ACCEPTED)
async def import_destinations_csv(
    file: Optional[Any] = None,
    csv_text: Optional[str] = Body(None, embed=True),
    safe_reachability: bool = False,
) -> Dict[str, Any]:
    """Imports destinations via CSV with deduplication, normalization, and job tracking."""
    from engine.catalogue_importer import catalogue_importer
    from core.jobs import job_manager

    content = ""
    if file and hasattr(file, "read"):
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8")
    elif csv_text:
        content = csv_text

    if not content.strip():
        raise IncuBrixError(
            code=ErrorCode.VALIDATION_ERROR,
            message="CSV content cannot be empty.",
            status_code=400,
        )

    job_id = job_manager.create_job(payload={"action": "catalogue_csv_import"})

    result = catalogue_importer.import_csv_content(
        csv_content=content,
        safe_reachability_check=safe_reachability,
        enrich_relevance=True,
        job_id=job_id,
    )

    # Populate catalogue store with imported records
    for d in result.destinations:
        new_id = str(uuid.uuid4())
        d["id"] = new_id
        d["level"] = "L0"
        d["created_at"] = datetime.now(timezone.utc).isoformat()
        _catalogue_store[new_id] = d

    return {
        "job_id": job_id,
        "status": "completed",
        "total_rows": result.total_rows,
        "imported_rows": result.imported_rows,
        "duplicate_rows": result.duplicate_rows,
        "invalid_rows": result.invalid_rows,
        "languages_detected": result.languages_detected,
        "error_report_download_url": result.error_report_download_url,
        "links": {"job": f"/api/v1/jobs/{job_id}"},
    }


@router.post("/{destination_id}/propose-rules", status_code=status.HTTP_200_OK)
async def propose_rules_for_destination(
    destination_id: str = Path(...),
    req: RuleProposeRequest = Body(...),
) -> Dict[str, Any]:
    """AI adapter-based step proposing community posting rules from guidelines text."""
    from engine.rule_capture import rule_capture_manager

    dest = _catalogue_store.get(destination_id)
    if not dest:
        raise IncuBrixError(code=ErrorCode.NOT_FOUND, message=f"Destination '{destination_id}' not found.", status_code=404)

    proposal = await rule_capture_manager.propose_rules(
        destination_id=destination_id,
        rules_text=req.rules_text,
        rules_url=req.rules_url,
    )
    return proposal.model_dump()


@router.post("/{destination_id}/confirm-rules", status_code=status.HTTP_200_OK)
async def confirm_rules_for_destination(
    destination_id: str = Path(...),
    req: RuleConfirmRequest = Body(...),
) -> Dict[str, Any]:
    """Human confirmation step required before activating proposed community rules."""
    from engine.rule_capture import rule_capture_manager

    dest = _catalogue_store.get(destination_id)
    if not dest:
        raise IncuBrixError(code=ErrorCode.NOT_FOUND, message=f"Destination '{destination_id}' not found.", status_code=404)

    params = dest.setdefault("parameters", {})
    record = rule_capture_manager.confirm_rules(
        proposal_id=req.proposal_id,
        destination_parameters=params,
        confirmed_by=req.confirmed_by or "human_operator",
    )
    return record.model_dump()

