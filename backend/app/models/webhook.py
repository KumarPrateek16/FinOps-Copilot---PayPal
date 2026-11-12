import uuid
from typing import Any, Dict
from sqlalchemy import String, ForeignKey, Uuid, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WebhookEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Raw PayPal webhook events for idempotency and audit tracking."""
    __tablename__ = "webhook_events"

    merchant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True)
    paypal_transmission_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)  # SUCCESS, FAILURE, SIMULATED
    processed_status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)     # PENDING, PROCESSED, FAILED
