import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Header, HTTPException, status
from pydantic import BaseModel, Field

from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError
from engine.publisher import publish_engine

router = APIRouter(prefix="/api/v1/publish", tags=["publish"])


class PublishRequestPayload(BaseModel):
    rendition: Rendition
    destination_ids: List[str] = Field(default_factory=list)
    destination: Optional[DestinationPayload] = None
    connection: Optional[ConnectionPayload] = None


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def publish_content(
    payload: PublishRequestPayload,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Dict[str, Any]:
    """Main publishing endpoint.

    Requires Idempotency-Key. Evaluates pre-flight posting rules, rate limits,
    executes connector dispatch, and reconciles on timeout.
    """
    if not idempotency_key:
        raise IncuBrixError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Missing required 'Idempotency-Key' header on publish request.",
            status_code=400,
        )

    # Determine target destination
    from api.routers.destinations import _catalogue_store

    dest_payload = payload.destination
    conn_payload = payload.connection or ConnectionPayload()

    if payload.destination_ids:
        dest_id = payload.destination_ids[0]
        stored_dest = _catalogue_store.get(dest_id)
        if not stored_dest:
            raise IncuBrixError(
                code=ErrorCode.NOT_FOUND,
                message=f"Destination '{dest_id}' not found in catalogue.",
                status_code=404,
            )
        dest_payload = DestinationPayload(
            id=stored_dest["id"],
            name=stored_dest["name"],
            url=stored_dest["url"],
            platform_key=stored_dest["platform_key"],
            surface=stored_dest["surface"],
            parameters=stored_dest.get("parameters", {}),
        )
        conn_dict = stored_dest.get("connection") or {}
        conn_payload = ConnectionPayload.model_validate(conn_dict)

    if not dest_payload:
        raise IncuBrixError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Must provide either destination_ids or destination object.",
            status_code=422,
        )

    job_id = f"job_{idempotency_key[:12]}"
    result = await publish_engine.publish(
        rendition=payload.rendition,
        destination=dest_payload,
        connection=conn_payload,
        idempotency_key=idempotency_key,
    )

    return {
        "job_id": job_id,
        "status": result.get("status", "queued"),
        "platform_post_id": result.get("platform_post_id"),
        "live_url": result.get("live_url"),
        "details": result,
    }
