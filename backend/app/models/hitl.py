import uuid
from datetime import datetime, timezone
from typing import Any, Dict, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, func, Uuid, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.dispute import Dispute


class HITLQueueItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Human-in-the-Loop review queue item triggered by policy thresholds."""
    __tablename__ = "hitl_queue_items"

    dispute_id: Mapped[str] = mapped_column(String(64), ForeignKey("disputes.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False)  # URGENT, HIGH, MEDIUM, LOW
    trigger_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    # EXCEEDS_AMOUNT_THRESHOLD, LOW_CONFIDENCE, CONFLICTING_EVIDENCE, MANUAL_OVERRIDE
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    # PENDING, APPROVED, REJECTED, EDITED_AND_APPROVED
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    dispute: Mapped["Dispute"] = relationship("Dispute", back_populates="hitl_item")
    audit_logs: Mapped[list["HITLAuditLog"]] = relationship("HITLAuditLog", back_populates="queue_item", cascade="all, delete-orphan")


class HITLAuditLog(Base, UUIDPrimaryKeyMixin):
    """Immutable audit trail for human interactions and reviews."""
    __tablename__ = "hitl_audit_logs"

    hitl_queue_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("hitl_queue_items.id", ondelete="CASCADE"), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    # VIEW, EDIT_EVIDENCE, APPROVE_SUBMISSION, REJECT_SUBMISSION, CONCEDE_DISPUTE
    previous_state: Mapped[Dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    new_state: Mapped[Dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    queue_item: Mapped["HITLQueueItem"] = relationship("HITLQueueItem", back_populates="audit_logs")
