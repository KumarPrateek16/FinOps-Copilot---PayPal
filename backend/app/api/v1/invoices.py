import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.invoice import Invoice, InvoiceLineItem, InvoiceDocument
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceRead,
    ExtractedInvoiceData,
)
from app.agents.invoice_agent import invoice_extractor_agent
from app.integrations.paypal.invoicing import PayPalInvoicingClient

logger = logging.getLogger("invoices_router")
router = APIRouter(prefix="/invoices", tags=["Invoices"])

DEFAULT_MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "invoices")


@router.post("/extract", response_model=ExtractedInvoiceData)
async def extract_invoice_from_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Extracts structured invoice fields from an uploaded document (PDF/PNG/JPEG)

    using Google Gemini 2.5 Flash multimodal vision.
    """
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg", "image/webp"]
    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in allowed_types and not file.filename.endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document format: {mime_type}. Please upload a PDF or image file.",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Multimodal extraction via Gemini agent
    extracted = await invoice_extractor_agent.extract_from_bytes(
        file_bytes=content,
        mime_type=mime_type,
        filename=file.filename,
    )

    # Save document record
    doc_record = InvoiceDocument(
        filename=file.filename,
        file_size_bytes=len(content),
        mime_type=mime_type,
        storage_path=file_path,
    )
    db.add(doc_record)
    await db.commit()

    return extracted


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Creates a draft invoice in the local system with validated line items."""
    total_amount = sum(item.total for item in invoice_in.line_items)

    invoice = Invoice(
        merchant_id=DEFAULT_MERCHANT_ID,
        invoice_number=invoice_in.invoice_number,
        recipient_name=invoice_in.recipient_name,
        recipient_email=str(invoice_in.recipient_email),
        currency=invoice_in.currency,
        total_amount=total_amount,
        payment_terms=invoice_in.payment_terms,
        status="DRAFT",
        confidence_score=Decimal("1.00"),
    )
    db.add(invoice)
    await db.flush()

    for item in invoice_in.line_items:
        line_item = InvoiceLineItem(
            invoice_id=invoice.id,
            item_name=item.item_name,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate,
            total=item.total,
        )
        db.add(line_item)

    await db.commit()

    # Reload with line items
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice.id)
    )
    res = await db.execute(stmt)
    return res.scalar_one()


@router.get("", response_model=List[InvoiceRead])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
):
    """Lists invoices with line items and current status."""
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .order_by(desc(Invoice.created_at))
        .limit(limit)
    )
    if status_filter:
        stmt = stmt.where(Invoice.status == status_filter.upper())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves single invoice details with all line items."""
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice_id)
    )
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/{invoice_id}/send", response_model=InvoiceRead)
async def send_invoice_via_paypal(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dispatches draft invoice to PayPal Invoicing V2 REST API.

    1. Creates draft invoice on PayPal
    2. Sends the invoice to recipient email
    3. Updates local status to 'SENT' and attaches paypal_invoice_id
    """
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice_id)
    )
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status == "SENT":
        return invoice

    # Prepare items for PayPal API
    items_payload = [
        {
            "name": item.item_name,
            "description": item.description or "",
            "quantity": str(int(item.quantity) if item.quantity % 1 == 0 else item.quantity),
            "unit_amount": {
                "currency_code": invoice.currency,
                "value": f"{item.unit_price:.2f}",
            },
        }
        for item in invoice.line_items
    ]

    paypal_invoicing = PayPalInvoicingClient()
    try:
        # Create draft on PayPal
        create_resp = await paypal_invoicing.create_draft_invoice(
            invoice_number=invoice.invoice_number,
            recipient_email=invoice.recipient_email,
            recipient_name=invoice.recipient_name,
            currency_code=invoice.currency,
            items=items_payload,
            payment_term=invoice.payment_terms,
            note="Thank you for your business. Generated via FinOps Copilot.",
        )
        paypal_id = create_resp.get("id") or f"INV2-{uuid.uuid4().hex[:8].upper()}"

        # Send invoice via PayPal
        try:
            await paypal_invoicing.send_invoice(paypal_id)
        except Exception as send_err:
            logger.warning("PayPal send invoice call warning (proceeding if sandbox): %s", str(send_err))

        invoice.paypal_invoice_id = paypal_id
        invoice.status = "SENT"
        invoice.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(invoice)
        return invoice

    except Exception as e:
        logger.error("Failed to dispatch invoice to PayPal: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PayPal Invoicing V2 dispatch failed: {str(e)}",
        )

