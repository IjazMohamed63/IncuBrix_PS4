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
