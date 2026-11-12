import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, TYPE_CHECKING
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Text, Uuid, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.merchant import Merchant
    from app.models.evidence import DisputeEvidence, DisputeSubmission
    from app.models.hitl import HITLQueueItem


class Dispute(Base, TimestampMixin):
    """PayPal Customer Dispute record with AI reasoning and HITL tracking."""
    __tablename__ = "disputes"

    # Primary key is the PayPal Dispute ID (e.g. PP-D-XXXXX)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=False)
    disputed_transaction_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    dispute_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    dispute_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)  # MERCHANDISE_OR_SERVICE_NOT_RECEIVED, etc.
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # WAITING_FOR_SELLER_RESPONSE, etc.
    lifecycle_stage: Mapped[str] = mapped_column(String(32), nullable=False)  # INQUIRY, CLAIM, etc.
    seller_response_due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # AI assessment
    ai_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    ai_risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)  # LOW, MEDIUM, HIGH
    ai_reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    defense_status: Mapped[str] = mapped_column(String(32), default="INGESTED", nullable=False)
    # INGESTED, EVIDENCE_GATHERED, IN_HITL_REVIEW, SUBMITTED, CONCEDED, CLOSED

    # Raw PayPal dispute payload
    raw_dispute_data: Mapped[Dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)

    # Relationships
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="disputes")
    evidences: Mapped[list["DisputeEvidence"]] = relationship("DisputeEvidence", back_populates="dispute", cascade="all, delete-orphan")
    submissions: Mapped[list["DisputeSubmission"]] = relationship("DisputeSubmission", back_populates="dispute", cascade="all, delete-orphan")
    hitl_item: Mapped["HITLQueueItem | None"] = relationship("HITLQueueItem", back_populates="dispute", uselist=False, cascade="all, delete-orphan")
