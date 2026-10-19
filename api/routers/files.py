from typing import Any, Dict, Optional
from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
import httpx
from pydantic import BaseModel, HttpUrl

from core.errors import ErrorCode, IncuBrixError
from core.manifest_builder import build_output_manifest
from core.ssrf import validate_url_ssrf_safe
from core.storage import DEFAULT_MAX_FILE_SIZE, storage_service

router = APIRouter(prefix="/api/v1/files", tags=["files"])


class FetchUrlRequest(BaseModel):
    url: str
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE
    allow_local_for_tests: bool = False


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """Uploads a file directly, validates size limit, stores it, and outputs manifest."""
    content = await file.read()
    stored = storage_service.store_file(
        data=content,
        filename=file.filename or "uploaded_file.bin",
        content_type=file.content_type or "application/octet-stream",
    )
    manifest = build_output_manifest(
        settings={"filename": stored["filename"], "size_bytes": stored["size_bytes"]},
        licence_rights="All rights reserved by uploader",
        ai_generated=False,
    )
    return {
        **stored,
        "manifest": manifest,
    }


@router.post("/fetch-url", status_code=status.HTTP_201_CREATED)
async def fetch_file_from_url(
    payload: FetchUrlRequest,
) -> Dict[str, Any]:
    """Fetches a file from a remote URL with SSRF-safe validation and size limits."""
    # 1. SSRF Validation
    safe_url = validate_url_ssrf_safe(payload.url, allow_local_for_tests=payload.allow_local_for_tests)

    # 2. Fetch with streaming size limit
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            head_res = await client.head(safe_url)
            content_length = head_res.headers.get("content-length")
            if content_length and int(content_length) > payload.max_size_bytes:
                raise IncuBrixError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"File exceeds maximum allowed size of {payload.max_size_bytes} bytes.",
                    status_code=413,
                )

            res = await client.get(safe_url)
            if res.status_code >= 400:
                raise IncuBrixError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Failed to fetch file from URL (status {res.status_code})",
                    status_code=400,
                )

            data = res.content
            if len(data) > payload.max_size_bytes:
                raise IncuBrixError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"File exceeds maximum allowed size of {payload.max_size_bytes} bytes.",
                    status_code=413,
                )

            filename = safe_url.split("/")[-1].split("?")[0] or "downloaded_file.bin"
            content_type = res.headers.get("content-type", "application/octet-stream")

            stored = storage_service.store_file(
                data=data,
                filename=filename,
                content_type=content_type,
                max_size_bytes=payload.max_size_bytes,
            )
            manifest = build_output_manifest(
                settings={"source_url": safe_url, "size_bytes": len(data)},
                licence_rights="unknown",
                ai_generated=False,
            )
            return {
                **stored,
                "manifest": manifest,
            }
    except IncuBrixError:
        raise
    except Exception as e:
        raise IncuBrixError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Error fetching URL '{payload.url}': {str(e)}",
            status_code=400,
        )


@router.get("/{file_id}/download")
async def download_file(file_id: str):
    """Downloads stored file content."""
    data, content_type = storage_service.get_file(file_id)
    return Response(content=data, media_type=content_type)
