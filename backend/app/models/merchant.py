import uuid
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import String, Numeric, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dispute import Dispute
    from app.models.invoice import Invoice
    from app.models.cashflow import FinancialSnapshot, FinancialAlert, MockOrder


class Merchant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Merchant account model storing PayPal integration settings and HITL thresholds."""
    __tablename__ = "merchants"

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    paypal_payer_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    paypal_client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    paypal_client_secret_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    webhook_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Configurable HITL policy settings
    hitl_auto_submit_threshold: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("50.00"),
        nullable=False,
    )
    hitl_min_confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("0.85"),
        nullable=False,
    )

    # Relationships
    disputes: Mapped[list["Dispute"]] = relationship("Dispute", back_populates="merchant", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="merchant", cascade="all, delete-orphan")
    snapshots: Mapped[list["FinancialSnapshot"]] = relationship("FinancialSnapshot", back_populates="merchant", cascade="all, delete-orphan")
    alerts: Mapped[list["FinancialAlert"]] = relationship("FinancialAlert", back_populates="merchant", cascade="all, delete-orphan")
    mock_orders: Mapped[list["MockOrder"]] = relationship("MockOrder", back_populates="merchant", cascade="all, delete-orphan")

