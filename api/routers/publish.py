import asyncio
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Body, Header, HTTPException, status
from pydantic import BaseModel, Field

from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError
from core.jobs import job_manager
from engine.publisher import publish_engine

router = APIRouter(prefix="/api/v1/publish", tags=["publish"])


class PublishRequestPayload(BaseModel):
    rendition: Rendition
    destination_ids: List[str] = Field(default_factory=list)
    destination: Optional[DestinationPayload] = None
    connection: Optional[ConnectionPayload] = None
    callback_url: Optional[str] = None
    async_mode: Optional[bool] = False


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def publish_content(
    payload: PublishRequestPayload,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Dict[str, Any]:
    """Main publishing endpoint.

    Requires Idempotency-Key. Evaluates pre-flight posting rules, rate limits,
    executes connector dispatch, and reconciles on timeout.
    Operations exceeding 2 seconds or requested in async mode return 202 + job_id.
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

    # Create durable background job persisted to disk
    job_summary = {
        "destination_id": dest_payload.id,
        "platform_key": dest_payload.platform_key,
        "title": payload.rendition.title,
    }
    job_id = job_manager.create_job(
        payload=job_summary,
        idempotency_key=idempotency_key,
        callback_url=payload.callback_url,
    )

    async def _execute_publish() -> Dict[str, Any]:
        job_manager.update_progress(job_id, 25, "running")
        try:
            result = await publish_engine.publish(
                rendition=payload.rendition,
                destination=dest_payload,
                connection=conn_payload,
                idempotency_key=idempotency_key,
            )
            result_links = {
                "live_url": result.get("live_url"),
                "platform_post_id": result.get("platform_post_id"),
                "job": f"/api/v1/jobs/{job_id}",
            }
            manifest = result.get("manifest")
            await job_manager.complete_job(
                job_id,
                result=result,
                result_links=result_links,
                manifest=manifest,
            )
            return result
        except Exception as e:
            await job_manager.fail_job(job_id, str(e))
            raise

    # If async_mode requested explicitly, return immediately
    if payload.async_mode:
        asyncio.create_task(_execute_publish())
        return {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "links": {"job": f"/api/v1/jobs/{job_id}"},
        }

    # Execute with 2.0s timeout: anything over 2 seconds returns 202 + job_id
    task = asyncio.create_task(_execute_publish())
    try:
        result = await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
        return {
            "job_id": job_id,
            "status": result.get("status", "succeeded"),
            "progress": 100,
            "platform_post_id": result.get("platform_post_id"),
            "live_url": result.get("live_url"),
            "manifest": result.get("manifest"),
            "result_links": {
                "live_url": result.get("live_url"),
                "job": f"/api/v1/jobs/{job_id}",
            },
            "details": result,
        }
    except asyncio.TimeoutError:
        job_manager.update_progress(job_id, 50, "running")
        return {
            "job_id": job_id,
            "status": "running",
            "progress": 50,
            "links": {"job": f"/api/v1/jobs/{job_id}"},
            "message": "Operation exceeded 2 seconds; execution continues in durable background job.",
        }
