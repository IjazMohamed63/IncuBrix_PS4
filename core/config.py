from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for IncuBrix Long-Tail Distribution Network."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime Environment
    app_env: str = "development"
    app_name: str = "incubrix-distribution"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    simulation_mode: bool = True

    # Database Configuration
    database_url: str = "postgresql+asyncpg://incubrix_user:incubrix_password@localhost:5432/incubrix_db"
    database_sync_url: Optional[str] = "postgresql://incubrix_user:incubrix_password@localhost:5432/incubrix_db"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # Storage (S3 / MinIO)
    s3_endpoint: str = "localhost:9000"
    s3_access_key: str = "incubrix_minio_admin"
    s3_secret_key: str = "incubrix_minio_secret_key_change_in_prod"
    s3_bucket_name: str = "incubrix-artifacts"
    s3_secure: bool = False

    # Security & Tokens
    webhook_signing_secret: str = "whsec_dev_placeholder_signing_key_32chars"
    api_access_token: str = "incubrix_demo_reviewer_token_2026"

    # Sandboxes & Mock Platforms
    mock_platforms_url: str = "http://localhost:8080"
    lemmy_api_url: str = "http://localhost:8536"
    ghost_api_url: str = "http://localhost:2368"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton instance."""
    return Settings()
