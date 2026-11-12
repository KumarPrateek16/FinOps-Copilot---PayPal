import io
import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tests.conftest import TestingSessionLocal
from app.models.merchant import Merchant
from app.agents.invoice_agent import invoice_extractor_agent
from app.schemas.invoice import InvoiceCreate, InvoiceLineItemCreate

TEST_MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture(autouse=True)
async def seed_merchant(setup_test_db):
    async with TestingSessionLocal() as session:
        merchant = Merchant(
            id=TEST_MERCHANT_ID,
            business_name="Test FinOps Merchant",
            paypal_payer_id="PAYER-FINOPS-001",
            paypal_client_id="client_test",
            paypal_client_secret_enc=b"enc",
            hitl_auto_submit_threshold=Decimal("50.00"),
            hitl_min_confidence_score=Decimal("0.85"),
        )
        session.add(merchant)
        await session.commit()


@pytest.mark.asyncio
async def test_invoice_extractor_fallback():
    sample_po_text = (
        "PURCHASE ORDER: PO-98432\n"
        "Bill To: Stark Industries Logistics\n"
        "Email: accounts@starkindustries.com\n"
        "Items: Precision Arc Capacitors - $450.00\n"
    )
    extracted = await invoice_extractor_agent.extract_from_bytes(
        file_bytes=sample_po_text.encode("utf-8"),
        mime_type="text/plain",
        filename="PO-98432.txt",
    )

    assert extracted.invoice_number == "PO-98432"
    assert "Stark Industries" in extracted.recipient_name
    assert extracted.recipient_email == "accounts@starkindustries.com"
    assert len(extracted.line_items) >= 1
    assert extracted.total_amount > 0
    assert extracted.confidence_score >= Decimal("0.80")


@pytest.mark.asyncio
async def test_extract_invoice_endpoint(async_client: AsyncClient):
    file_content = b"PURCHASE ORDER: PO-2026-X\nCustomer: Wayne Enterprises\nEmail: procurement@wayne.com\n"
    files = {"file": ("purchase_order.pdf", io.BytesIO(file_content), "application/pdf")}

    response = await async_client.post("/api/v1/invoices/extract", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "PO-2026-X" in data["invoice_number"]
    assert "Wayne Enterprises" in data["recipient_name"]
    assert data["recipient_email"] == "procurement@wayne.com"
    assert len(data["line_items"]) >= 1


@pytest.mark.asyncio
async def test_create_and_get_invoice(async_client: AsyncClient):
    invoice_payload = {
        "invoice_number": "INV-2026-001",
        "recipient_name": "Cyberdyne Systems",
        "recipient_email": "billing@cyberdyne.com",
        "currency": "USD",
        "payment_terms": "DUE_ON_RECEIPT",
        "line_items": [
            {
                "item_name": "Neural Net Processing Units",
                "description": "Enterprise AI accelerator cards",
                "quantity": 2.0,
                "unit_price": 600.0,
                "tax_rate": 0.0,
                "total": 1200.0,
            },
            {
                "item_name": "Installation Service",
                "description": "Onsite calibration",
                "quantity": 1.0,
                "unit_price": 300.0,
                "tax_rate": 0.0,
                "total": 300.0,
            },
        ],
    }

    create_resp = await async_client.post("/api/v1/invoices", json=invoice_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["invoice_number"] == "INV-2026-001"
    assert float(created["total_amount"]) == 1500.0
    assert created["status"] == "DRAFT"
    assert len(created["line_items"]) == 2
    invoice_id = created["id"]

    # Detail GET
    get_resp = await async_client.get(f"/api/v1/invoices/{invoice_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == invoice_id
    assert fetched["recipient_name"] == "Cyberdyne Systems"

    # List GET
    list_resp = await async_client.get("/api/v1/invoices")
    assert list_resp.status_code == 200
    invoices_list = list_resp.json()
    assert any(inv["id"] == invoice_id for inv in invoices_list)


@pytest.mark.asyncio
async def test_send_invoice_paypal(async_client: AsyncClient):
    # First create an invoice
    invoice_payload = {
        "invoice_number": "INV-PP-099",
        "recipient_name": "Wayne Enterprises",
        "recipient_email": "ap@wayne.com",
        "currency": "USD",
        "payment_terms": "DUE_ON_RECEIPT",
        "line_items": [
            {
                "item_name": "Custom Hardware Module",
                "description": "Secured communications module",
                "quantity": 1.0,
                "unit_price": 500.0,
                "tax_rate": 0.0,
                "total": 500.0,
            }
        ],
    }
    create_resp = await async_client.post("/api/v1/invoices", json=invoice_payload)
    assert create_resp.status_code == 201
    invoice_id = create_resp.json()["id"]

    # Mock PayPalInvoicingClient
    with patch("app.api.v1.invoices.PayPalInvoicingClient.create_draft_invoice", new_callable=AsyncMock) as mock_create, \
         patch("app.api.v1.invoices.PayPalInvoicingClient.send_invoice", new_callable=AsyncMock) as mock_send:

        mock_create.return_value = {"id": "INV2-SANDBOX-TEST-999"}
        mock_send.return_value = {"status": "SENT"}

        send_resp = await async_client.post(f"/api/v1/invoices/{invoice_id}/send")
        assert send_resp.status_code == 200
        sent_data = send_resp.json()
        assert sent_data["status"] == "SENT"
        assert sent_data["paypal_invoice_id"] == "INV2-SANDBOX-TEST-999"
        mock_create.assert_awaited_once()
        mock_send.assert_awaited_once_with("INV2-SANDBOX-TEST-999")

