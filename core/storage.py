import io
from typing import Optional
from minio import Minio
from core.config import get_settings
from core.logging import get_logger

logger = get_logger("storage")
settings = get_settings()


class StorageClient:
    """MinIO S3-compatible client for storing evidence packs, media, and outputs."""

    def __init__(self):
        self.endpoint = settings.s3_endpoint
        self.access_key = settings.s3_access_key
        self.secret_key = settings.s3_secret_key
        self.secure = settings.s3_secure
        self.bucket = settings.s3_bucket_name
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def ensure_bucket(self) -> None:
        """Ensures that the default bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created S3 bucket '{self.bucket}'")
        except Exception as e:
            logger.warning(f"Failed to verify/create S3 bucket '{self.bucket}': {str(e)}")

    def upload_bytes(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Uploads raw bytes to MinIO and returns the object reference URI."""
        stream = io.BytesIO(data)
        self.client.put_object(
            self.bucket,
            object_name,
            stream,
            length=len(data),
            content_type=content_type,
        )
        return f"s3://{self.bucket}/{object_name}"

    def check_health(self) -> bool:
        """Probes the S3 service for health check."""
        try:
            self.client.bucket_exists(self.bucket)
            return True
        except Exception as e:
            logger.warning(f"S3 storage health check failed: {str(e)}")
            return False


storage = StorageClient()
