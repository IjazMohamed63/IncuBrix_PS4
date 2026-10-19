import hashlib
import io
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import uuid

from core.config import get_settings
from core.errors import ErrorCode, IncuBrixError
from core.logging import get_logger

logger = get_logger("storage")
settings = get_settings()

DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB default limit


class StorageService:
    """Handles object persistence with MinIO S3 and local filesystem fallback."""

    def __init__(self, local_storage_dir: Optional[str] = None):
        self.settings = get_settings()
        self.bucket_name = self.settings.s3_bucket_name
        self.local_dir = Path(local_storage_dir or "storage_artifacts")
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self._minio_client = None
        self._minio_available: Optional[bool] = None

    def _get_minio_client(self):
        if self._minio_available is False:
            return None
        if self._minio_client is not None:
            return self._minio_client

        # Fast socket check before initializing MinIO to avoid urllib3 retry delays
        try:
            import socket
            host, port_str = self.settings.s3_endpoint.split(":")
            with socket.create_connection((host, int(port_str)), timeout=0.1):
                pass
        except Exception:
            self._minio_available = False
            return None

        try:
            from minio import Minio
            client = Minio(
                endpoint=self.settings.s3_endpoint,
                access_key=self.settings.s3_access_key,
                secret_key=self.settings.s3_secret_key,
                secure=self.settings.s3_secure,
            )
            # If server is reachable, ensure bucket exists
            if not client.bucket_exists(self.bucket_name):
                client.make_bucket(self.bucket_name)
            self._minio_client = client
            self._minio_available = True
            logger.info(f"Connected to MinIO at {self.settings.s3_endpoint}, bucket: {self.bucket_name}")
            return self._minio_client
        except Exception as e:
            logger.info(f"MinIO not reachable ({e}). Falling back to local storage engine: {self.local_dir}")
            self._minio_available = False
            return None

    def store_file(
        self,
        data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        max_size_bytes: int = DEFAULT_MAX_FILE_SIZE,
    ) -> Dict[str, Any]:
        """Stores file content to MinIO or local storage if size is within limits."""
        if len(data) > max_size_bytes:
            raise IncuBrixError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"File exceeds maximum allowed size of {max_size_bytes} bytes (got {len(data)} bytes).",
                status_code=413,
                details={"max_size_bytes": max_size_bytes, "file_size": len(data)},
            )

        file_id = f"file_{uuid.uuid4().hex[:16]}"
        sha256 = hashlib.sha256(data).hexdigest()
        ext = Path(filename).suffix
        object_name = f"{file_id}{ext}"

        client = self._get_minio_client()
        if client:
            try:
                data_stream = io.BytesIO(data)
                client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=data_stream,
                    length=len(data),
                    content_type=content_type,
                )
                download_url = f"http://{self.settings.s3_endpoint}/{self.bucket_name}/{object_name}"
                return {
                    "file_id": file_id,
                    "filename": filename,
                    "object_name": object_name,
                    "size_bytes": len(data),
                    "sha256": sha256,
                    "content_type": content_type,
                    "storage_backend": "minio",
                    "download_url": download_url,
                }
            except Exception as e:
                logger.warning(f"MinIO put_object failed ({e}), writing to local disk.")

        # Local storage fallback
        dest_path = self.local_dir / object_name
        dest_path.write_bytes(data)
        download_url = f"/api/v1/files/{file_id}/download"

        return {
            "file_id": file_id,
            "filename": filename,
            "object_name": object_name,
            "size_bytes": len(data),
            "sha256": sha256,
            "content_type": content_type,
            "storage_backend": "local",
            "download_url": download_url,
            "local_path": str(dest_path),
        }

    def get_file(self, file_id_or_object_name: str) -> Tuple[bytes, str]:
        """Retrieves stored file bytes and content type."""
        # Check local files first
        for f in self.local_dir.glob(f"{file_id_or_object_name}*"):
            if f.is_file():
                return f.read_bytes(), "application/octet-stream"

        # Check MinIO
        client = self._get_minio_client()
        if client:
            try:
                response = client.get_object(self.bucket_name, file_id_or_object_name)
                data = response.read()
                response.close()
                response.release_conn()
                return data, "application/octet-stream"
            except Exception as e:
                raise IncuBrixError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"File '{file_id_or_object_name}' not found: {e}",
                    status_code=404,
                )

        raise IncuBrixError(
            code=ErrorCode.NOT_FOUND,
            message=f"File '{file_id_or_object_name}' not found.",
            status_code=404,
        )

    def check_health(self) -> bool:
        """Readiness check for storage service."""
        try:
            return self.local_dir.exists()
        except Exception:
            return False


storage_service = StorageService()
storage = storage_service

