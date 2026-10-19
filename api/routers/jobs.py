from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from core.errors import ErrorCode, IncuBrixError
from core.jobs import job_manager

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    payload: Dict[str, Any]
    callback_url: Optional[str] = None
    idempotency_key: Optional[str] = None


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_background_job(
    request: CreateJobRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Dict[str, Any]:
    """Creates a durable background job and returns 202 + job_id."""
    key = idempotency_key or request.idempotency_key or f"job_key_{uuid.uuid4().hex[:8]}"
    job_id = job_manager.create_job(
        payload=request.payload,
        idempotency_key=key,
        callback_url=request.callback_url,
    )
    return {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "links": {"self": f"/api/v1/jobs/{job_id}"},
    }


@router.get("/{job_id}")
async def get_background_job(job_id: str) -> Dict[str, Any]:
    """Retrieves current job status, progress 0-100, and result links."""
    job = job_manager.get_job(job_id)
    if not job:
        raise IncuBrixError(
            code=ErrorCode.NOT_FOUND,
            message=f"Job '{job_id}' not found.",
            status_code=404,
        )

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "result_links": job["result_links"],
        "result": job["result"],
        "manifest": job["manifest"],
        "error_message": job["error_message"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }
