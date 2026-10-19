import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, TimestampMixin


class PostingRule(Base, TimestampMixin):
    """Specific posting rule enforced on a destination."""
    __tablename__ = "posting_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)

    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)  # frequency_cap, self_promo, link_policy, ai_disclosure
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_human_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RuleDecisionAudit(Base, TimestampMixin):
    """Audit log capturing every rule engine evaluation decision."""
    __tablename__ = "rule_decision_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    destination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)

    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # ALLOW, BLOCK, RESCHEDULE
    rule_violated: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    next_allowed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    human_action_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
