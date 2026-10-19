import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, TimestampMixin


class PublishJob(Base, TimestampMixin):
    """Represents a background publishing job."""
    __tablename__ = "publish_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)  # queued, running, succeeded, failed, cancelled
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    callback_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    manifest_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    records = relationship("PublishRecord", back_populates="job", cascade="all, delete-orphan")


class PublishRecord(Base, TimestampMixin):
    """Represents publication state to an individual destination within a job."""
    __tablename__ = "publish_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("publish_jobs.id", ondelete="CASCADE"), nullable=False)
    destination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    live_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    tailored_rendition: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    evidence_s3_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    job = relationship("PublishJob", back_populates="records")
    destination = relationship("Destination", back_populates="publish_records")
