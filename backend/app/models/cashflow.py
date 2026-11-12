import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, TYPE_CHECKING
from sqlalchemy import String, Numeric, Integer, Boolean, Date, DateTime, ForeignKey, Text, Uuid, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.merchant import Merchant


class FinancialSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Periodic liquidity snapshot capturing balance, reserves, and dispute velocity."""
    __tablename__ = "financial_snapshots"

    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_dispute_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    active_dispute_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dispute_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    thirty_day_volume: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="snapshots")


class FinancialAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Proactive financial risk alert triggered by Cashflow Sentinel."""
    __tablename__ = "financial_alerts"

    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="WARNING", nullable=False)  # CRITICAL, WARNING, INFO
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="alerts")


class MockOrder(Base, TimestampMixin):
    """Internal merchant order and fulfillment database used for dispute evidence aggregation."""
    __tablename__ = "mock_orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. ORD-88291
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=False)
    paypal_transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_carrier: Mapped[str] = mapped_column(String(32), nullable=False)  # FEDEX, UPS, USPS
    tracking_number: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False)  # DELIVERED, IN_TRANSIT, RETURNED
    delivery_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    item_details: Mapped[Dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)

    # Relationships
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="mock_orders")
