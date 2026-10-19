import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, TimestampMixin


class Destination(Base, TimestampMixin):
    """Destination record representing one specific community, forum, or audience channel.

    Matches all 20 fields required by the IncuBrix catalogue specification.
    """
    __tablename__ = "destinations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core Identifiers
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    platform_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    surface: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")

    # Audience & Demographics
    audience_tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    geo: Mapped[str] = mapped_column(String(32), nullable=False, default="global")
    est_audience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Community Rules & Policy
    rules_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    frequency_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=24)  # hours between posts
    self_promo_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    link_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="allowed")  # allowed, none, whitelist
    disclosure_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    automation_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Connector & Scoring
    connector_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=3)  # 1 to 5
    relevance_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Maturity & Certification Level
    level: Mapped[str] = mapped_column(String(8), nullable=False, default="L0")  # L0, L1, L2, L3, L4
    last_certified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    connections = relationship("Connection", back_populates="destination", cascade="all, delete-orphan")
    publish_records = relationship("PublishRecord", back_populates="destination", cascade="all, delete-orphan")
    certification_runs = relationship("CertificationRun", back_populates="destination", cascade="all, delete-orphan")
