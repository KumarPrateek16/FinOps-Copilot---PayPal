import uuid
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr


class InvoiceLineItemBase(BaseModel):
    item_name: str = Field(..., max_length=255)
    description: str | None = None
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    total: Decimal = Field(..., ge=0)


class InvoiceLineItemCreate(InvoiceLineItemBase):
    pass


class InvoiceLineItemRead(InvoiceLineItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class InvoiceCreate(BaseModel):
    invoice_number: str
    recipient_name: str
    recipient_email: EmailStr
    currency: str = "USD"
    payment_terms: str = "DUE_ON_RECEIPT"
    line_items: List[InvoiceLineItemCreate]


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    paypal_invoice_id: str | None
    invoice_number: str
    recipient_name: str
    recipient_email: str
    currency: str
    total_amount: Decimal
    payment_terms: str
    status: str
    confidence_score: Decimal | None
    created_at: datetime
    updated_at: datetime
    line_items: List[InvoiceLineItemRead] = []


class ExtractedInvoiceData(BaseModel):
    invoice_number: str
    recipient_name: str
    recipient_email: str
    currency: str = "USD"
    payment_terms: str = "DUE_ON_RECEIPT"
    line_items: List[InvoiceLineItemCreate]
    total_amount: Decimal
    confidence_score: Decimal = Field(ge=0, le=1)
    notes: str | None = None

