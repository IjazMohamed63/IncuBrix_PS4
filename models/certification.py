import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, TimestampMixin


class CertificationRun(Base, TimestampMixin):
    """Tracks end-to-end certification execution against a destination."""
    __tablename__ = "certification_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    connector_key: Mapped[str] = mapped_column(String(64), nullable=False)

    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")  # running, succeeded, failed
    target_level: Mapped[str] = mapped_column(String(8), nullable=False, default="L3")
    assigned_level: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    step_results: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_s3_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    destination = relationship("Destination", back_populates="certification_runs")


class DeletionWatchdog(Base, TimestampMixin):
    """Guarantees test posts are deleted within 10 minutes (600s)."""
    __tablename__ = "deletion_watchdogs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certification_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("certification_runs.id", ondelete="CASCADE"), nullable=False)
    platform_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
