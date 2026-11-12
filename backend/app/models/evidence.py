import uuid
from datetime import datetime, timezone
from typing import Any, Dict, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, func, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dispute import Dispute


class DisputeEvidence(Base, UUIDPrimaryKeyMixin):
    """Supporting evidence item with source provenance tracking."""
    __tablename__ = "dispute_evidences"

    dispute_id: Mapped[str] = mapped_column(String(64), ForeignKey("disputes.id", ondelete="CASCADE"), index=True, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # PROOF_OF_FULFILLMENT, PROOF_OF_REFUND, POLICIES, COMMUNICATION, OTHER
    provenance_source: Mapped[str] = mapped_column(String(64), nullable=False)
    # INTERNAL_ORDER_DB, CARRIER_API, EMAIL_ARCHIVE, CUSTOMER_SERVICE
    source_reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_summary: Mapped[str] = mapped_column(Text, nullable=False)
    document_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_info: Mapped[Dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    dispute: Mapped["Dispute"] = relationship("Dispute", back_populates="evidences")


class DisputeSubmission(Base, UUIDPrimaryKeyMixin):
    """Record of an action submitted to PayPal Customer Disputes API."""
    __tablename__ = "dispute_submissions"

    dispute_id: Mapped[str] = mapped_column(String(64), ForeignKey("disputes.id", ondelete="CASCADE"), index=True, nullable=False)
    action_taken: Mapped[str] = mapped_column(String(32), nullable=False)  # PROVIDE_EVIDENCE, ACCEPT_CLAIM
    submitted_by: Mapped[str] = mapped_column(String(32), nullable=False)  # AUTONOMOUS_AGENT, MERCHANT_HITL
    submission_payload: Mapped[Dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    paypal_response_code: Mapped[int] = mapped_column(Integer, nullable=False)
    paypal_response_body: Mapped[Dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    dispute: Mapped["Dispute"] = relationship("Dispute", back_populates="submissions")
