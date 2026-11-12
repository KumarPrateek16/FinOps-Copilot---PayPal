import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.integrations.paypal.auth import PayPalAuthManager
from app.integrations.paypal.client import PayPalBaseClient
from app.integrations.paypal.disputes import PayPalDisputesClient
from app.integrations.paypal.invoicing import PayPalInvoicingClient
from app.integrations.shipping.carrier_mock import carrier_service


@pytest.mark.asyncio
async def test_auth_manager_token_caching():
    """Verifies that PayPalAuthManager caches access tokens and avoids duplicate requests."""
    auth_mgr = PayPalAuthManager(client_id="test_id", client_secret="test_secret")

    fake_response = {"access_token": "ACCESS_TOKEN_ABC123", "expires_in": 32400}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        # First call fetches token
        token1 = await auth_mgr.get_access_token()
        assert token1 == "ACCESS_TOKEN_ABC123"
        assert mock_post.call_count == 1

        # Second call returns cached token without HTTP call
        token2 = await auth_mgr.get_access_token()
        assert token2 == "ACCESS_TOKEN_ABC123"
        assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_disputes_client_provide_evidence():
    """Verifies that PayPalDisputesClient calls POST /v1/customer/disputes/{id}/provide-evidence with correct schema."""
    base_client = AsyncMock(spec=PayPalBaseClient)
    base_client.request = AsyncMock(return_value={"status": "EVIDENCE_SUBMITTED"})

    disputes_client = PayPalDisputesClient(client=base_client)

    resp = await disputes_client.provide_evidence(
        dispute_id="PP-D-12345",
        evidence_type="PROOF_OF_FULFILLMENT",
        notes="Package confirmed delivered via FedEx tracking.",
        tracking_info=[{"carrier_name": "FEDEX", "tracking_number": "TRK-998811"}],
    )

    assert resp == {"status": "EVIDENCE_SUBMITTED"}
    base_client.request.assert_called_once_with(
        method="POST",
        path="/v1/customer/disputes/PP-D-12345/provide-evidence",
        json_data={
            "evidences": [
                {
                    "evidence_type": "PROOF_OF_FULFILLMENT",
                    "notes": "Package confirmed delivered via FedEx tracking.",
                    "evidence_info": {
                        "tracking_info": [{"carrier_name": "FEDEX", "tracking_number": "TRK-998811"}]
                    },
                }
            ]
        },
    )


@pytest.mark.asyncio
async def test_invoicing_client_create_and_send():
    """Verifies invoice creation and send operations."""
    base_client = AsyncMock(spec=PayPalBaseClient)
    base_client.request = AsyncMock()

    invoicing_client = PayPalInvoicingClient(client=base_client)

    # 1. Next invoice number
    base_client.request.return_value = {"invoice_number": "INV2-0001"}
    inv_num = await invoicing_client.generate_next_invoice_number()
    assert inv_num == "INV2-0001"

    # 2. Create draft invoice
    base_client.request.return_value = {"id": "INV2-XYZ", "status": "DRAFT"}
    draft = await invoicing_client.create_draft_invoice(
        invoice_number="INV2-0001",
        recipient_email="client@example.com",
        recipient_name="Acme Client",
        currency_code="USD",
        items=[{"name": "Consulting", "quantity": "1", "unit_amount": {"currency_code": "USD", "value": "100.00"}}],
    )
    assert draft["id"] == "INV2-XYZ"
    assert draft["status"] == "DRAFT"

    # 3. Send invoice
    base_client.request.return_value = {"status": "SENT"}
    send_resp = await invoicing_client.send_invoice("INV2-XYZ")
    assert send_resp["status"] == "SENT"


@pytest.mark.asyncio
async def test_carrier_mock_tracking():
    """Verifies that the mock carrier service returns delivery proof checkpoints."""
    carrier_service.register_tracking(
        tracking_number="TRK-TEST-999",
        carrier="FEDEX",
        status="DELIVERED",
        recipient_name="Mark Test",
        delivery_days_ago=3,
        destination_city="San Jose",
        destination_state="CA",
    )

    info = await carrier_service.get_tracking_info("TRK-TEST-999")
    assert info is not None
    assert info["carrier"] == "FEDEX"
    assert info["status"] == "DELIVERED"
    assert info["signed_by"] == "Mark Test"
    assert len(info["events"]) == 3
