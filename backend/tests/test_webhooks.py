import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhook_ingestion_and_idempotency(async_client: AsyncClient):
    """Tests webhook endpoint signature acceptance and duplicate event deduplication."""
    payload = {
        "id": "WH-EVT-001",
        "event_version": "1.0",
        "create_time": "2026-11-10T00:00:00Z",
        "resource_type": "dispute",
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "summary": "Dispute created by buyer",
        "resource": {
            "dispute_id": "PP-D-998811",
            "dispute_amount": {"currency_code": "USD", "value": "45.00"},
            "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "seller_response_due_date": "2026-11-20T00:00:00Z",
            "disputed_transactions": [{"seller_transaction_id": "TXN-PP-001"}],
        },
    }

    headers = {
        "PAYPAL-TRANSMISSION-ID": "TRANS-UUID-TEST-001",
        "PAYPAL-TRANSMISSION-TIME": "2026-11-10T00:00:00Z",
        "PAYPAL-CERT-URL": "https://api-m.sandbox.paypal.com/v1/notifications/certs/CERT-SIMULATED",
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-TRANSMISSION-SIG": "VALID_SIGNATURE_MOCK",
    }

    # Mock signature verifier to return True immediately without network call
    with patch("app.api.v1.webhooks.webhook_verifier.verify_signature", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True

        # 1. First transmission should be accepted
        response = await async_client.post("/api/v1/webhooks/paypal", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["event_type"] == "CUSTOMER.DISPUTE.CREATED"
        assert data["transmission_id"] == "TRANS-UUID-TEST-001"

        # 2. Second transmission with SAME transmission ID must be recognized as duplicate
        dup_response = await async_client.post("/api/v1/webhooks/paypal", json=payload, headers=headers)
        assert dup_response.status_code == 200
        dup_data = dup_response.json()
        assert dup_data["status"] == "duplicate_ignored"
