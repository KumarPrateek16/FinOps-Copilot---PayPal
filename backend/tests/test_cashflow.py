import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from tests.conftest import TestingSessionLocal
from app.models.merchant import Merchant
from app.models.dispute import Dispute
from app.models.cashflow import FinancialSnapshot, FinancialAlert, MockOrder
from app.services.cashflow_service import cashflow_service

TEST_MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture(autouse=True)
async def seed_merchant_and_data(setup_test_db):
    async with TestingSessionLocal() as session:
        merchant = Merchant(
            id=TEST_MERCHANT_ID,
            business_name="Acme FinOps Merchant",
            paypal_payer_id="PAYER-ACME-001",
            paypal_client_id="client_test",
            paypal_client_secret_enc=b"enc",
            hitl_auto_submit_threshold=Decimal("50.00"),
            hitl_min_confidence_score=Decimal("0.85"),
        )
        session.add(merchant)

        # Add 10 mock orders in the last 30 days
        for i in range(10):
            order = MockOrder(
                id=f"ORD-MOCK-{i}",
                merchant_id=TEST_MERCHANT_ID,
                paypal_transaction_id=f"TXN-MOCK-{i}",
                customer_name=f"Customer {i}",
                customer_email=f"customer{i}@example.com",
                shipping_carrier="FEDEX",
                tracking_number=f"TRK-MOCK-{i}",
                delivery_status="DELIVERED",
                created_at=datetime.now(timezone.utc) - timedelta(days=i),
                item_details={"item": "Widget", "price": 50.00},
            )
            session.add(order)

        # Add 2 active disputes
        d1 = Dispute(
            id="PP-D-ALERT-001",
            merchant_id=TEST_MERCHANT_ID,
            disputed_transaction_id="TXN-MOCK-1",
            dispute_amount=Decimal("120.00"),
            dispute_currency="USD",
            reason="MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            status="WAITING_FOR_SELLER_RESPONSE",
            lifecycle_stage="CLAIM",
            seller_response_due_date=datetime.now(timezone.utc) + timedelta(days=10),
            defense_status="INGESTED",
            raw_dispute_data={"test": True},
        )
        d2 = Dispute(
            id="PP-D-ALERT-002",
            merchant_id=TEST_MERCHANT_ID,
            disputed_transaction_id="TXN-MOCK-2",
            dispute_amount=Decimal("80.00"),
            dispute_currency="USD",
            reason="MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            status="UNDER_REVIEW",
            lifecycle_stage="CLAIM",
            seller_response_due_date=datetime.now(timezone.utc) + timedelta(days=10),
            defense_status="IN_HITL_REVIEW",
            raw_dispute_data={"test": True},
        )
        session.add(d1)
        session.add(d2)

        await session.commit()


@pytest.mark.asyncio
async def test_cashflow_service_sync_and_snapshot():
    async with TestingSessionLocal() as session:
        snapshot = await cashflow_service.calculate_and_sync_metrics(session, TEST_MERCHANT_ID)

        assert snapshot.merchant_id == TEST_MERCHANT_ID
        assert snapshot.snapshot_date == date.today()
        assert snapshot.available_balance > 0
        assert snapshot.active_dispute_count == 2
        assert snapshot.total_dispute_amount == Decimal("200.00")
        assert snapshot.dispute_rate_pct > Decimal("0.00")


@pytest.mark.asyncio
async def test_cashflow_critical_rate_alert():
    """Verify that high dispute volume triggers CRITICAL dispute rate alert."""
    async with TestingSessionLocal() as session:
        # Add 5 more disputes to push rate > 1.0%
        for i in range(3, 8):
            disp = Dispute(
                id=f"PP-D-BURST-{i}",
                merchant_id=TEST_MERCHANT_ID,
                disputed_transaction_id=f"TXN-MOCK-{i}",
                dispute_amount=Decimal("50.00"),
                dispute_currency="USD",
                reason="UNAUTHORISED",
                status="WAITING_FOR_SELLER_RESPONSE",
                lifecycle_stage="CLAIM",
                seller_response_due_date=datetime.now(timezone.utc) + timedelta(days=10),
                defense_status="INGESTED",
                raw_dispute_data={"test": True},
            )
            session.add(disp)
        await session.commit()

        snapshot = await cashflow_service.calculate_and_sync_metrics(session, TEST_MERCHANT_ID)
        # 7 disputes / 120 baseline = ~5.83% > 1.0%
        assert snapshot.dispute_rate_pct >= Decimal("1.00")

        # Verify FinancialAlert created
        alert_res = await session.execute(
            FinancialAlert.__table__.select().where(
                FinancialAlert.merchant_id == TEST_MERCHANT_ID,
                FinancialAlert.alert_type == "DISPUTE_RATE_CRITICAL",
            )
        )
        alert = alert_res.first()
        assert alert is not None
        assert alert.severity == "CRITICAL"


@pytest.mark.asyncio
async def test_cashflow_metrics_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/cashflow/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "available_balance" in data
    assert "pending_balance" in data
    assert "dispute_rate_pct" in data
    assert "historical_snapshots" in data
    assert "active_alerts" in data
    assert data["active_dispute_count"] == 2


@pytest.mark.asyncio
async def test_cashflow_sync_and_acknowledge_alert(async_client: AsyncClient):
    # Trigger sync
    sync_resp = await async_client.post("/api/v1/cashflow/sync")
    assert sync_resp.status_code == 200
    data = sync_resp.json()
    assert float(data["total_dispute_amount"]) == 200.0

    # Get alerts
    alerts_resp = await async_client.get("/api/v1/cashflow/alerts")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()

    if len(alerts) > 0:
        alert_id = alerts[0]["id"]
        ack_resp = await async_client.post(f"/api/v1/cashflow/alerts/{alert_id}/acknowledge")
        assert ack_resp.status_code == 200
        assert ack_resp.json()["is_acknowledged"] is True

