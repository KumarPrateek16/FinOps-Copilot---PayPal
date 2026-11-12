import uuid
from decimal import Decimal
from typing import Any, Dict, TYPE_CHECKING
from sqlalchemy import String, Numeric, Integer, ForeignKey, Text, Uuid, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.merchant import Merchant


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Invoice generated via multimodal document extraction and sent via PayPal Invoicing V2."""
    __tablename__ = "invoices"

    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True, nullable=False)
    paypal_invoice_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_terms: Mapped[str] = mapped_column(String(32), default="DUE_ON_RECEIPT", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)  # DRAFT, SENT, PAID, CANCELLED
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    raw_extraction: Mapped[Dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="invoices")
    line_items: Mapped[list["InvoiceLineItem"]] = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    documents: Mapped[list["InvoiceDocument"]] = relationship("InvoiceDocument", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base, UUIDPrimaryKeyMixin):
    """Line item belonging to an invoice."""
    __tablename__ = "invoice_line_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1.00"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="line_items")


class InvoiceDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Source file uploaded by merchant for multimodal invoice extraction."""
    __tablename__ = "invoice_documents"

    invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("invoices.id", ondelete="SET NULL"), index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # Relationships
    invoice: Mapped["Invoice | None"] = relationship("Invoice", back_populates="documents")
