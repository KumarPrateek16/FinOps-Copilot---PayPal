import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.base import Base
from app.database.session import engine
from app.models.merchant import Merchant
from app.models.dispute import Dispute
from app.models.evidence import DisputeEvidence
from app.models.hitl import HITLQueueItem
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.cashflow import MockOrder, FinancialSnapshot, FinancialAlert
from app.integrations.shipping.carrier_mock import carrier_service

logger = logging.getLogger("seed")
logging.basicConfig(level=logging.INFO)

DEFAULT_MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


async def seed_data():
    """Initializes the database with sample merchant, orders, tracking data,

    realistic dispute claims, invoices, and cashflow snapshots.
    """
    logger.info("Starting database seed script...")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Create or retrieve default test merchant
        result = await session.execute(select(Merchant).where(Merchant.id == DEFAULT_MERCHANT_ID))
        merchant = result.scalar_one_or_none()

        if not merchant:
            logger.info("Creating default test merchant Acme Commerce...")
            merchant = Merchant(
                id=DEFAULT_MERCHANT_ID,
                business_name="Acme Electronics & Commerce",
                paypal_payer_id="PAYER-ACME-8821",
                paypal_client_id="sandbox_client_id_placeholder",
                paypal_client_secret_enc=b"encrypted_placeholder",
                webhook_id="WH-SANDBOX-TEST",
                hitl_auto_submit_threshold=Decimal("50.00"),
                hitl_min_confidence_score=Decimal("0.85"),
            )
            session.add(merchant)
            await session.flush()
        else:
            logger.info("Merchant %s already exists.", merchant.business_name)

        # 2. Seed Mock Orders and Carrier Tracking
        sample_orders = [
            {
                "id": "ORD-99101",
                "txn_id": "TXN-PP-001",
                "customer": "John Doe",
                "email": "johndoe@example.com",
                "carrier": "FEDEX",
                "tracking": "TRK-FDX-998811",
                "days_ago": 4,
                "city": "Austin",
                "state": "TX",
                "items": {"name": "Sony WH-1000XM5 Headphones", "price": 39.99, "qty": 1},
            },
            {
                "id": "ORD-99102",
                "txn_id": "TXN-PP-002",
                "customer": "Sarah Connor",
                "email": "sarah.c@example.com",
                "carrier": "UPS",
                "tracking": "TRK-UPS-774422",
                "days_ago": 7,
                "city": "Los Angeles",
                "state": "CA",
                "items": {"name": "Apple MacBook Air M3", "price": 1199.00, "qty": 1},
            },
            {
                "id": "ORD-99103",
                "txn_id": "TXN-PP-003",
                "customer": "Alice Smith",
                "email": "alice.smith@example.com",
                "carrier": "USPS",
                "tracking": "TRK-USPS-332211",
                "days_ago": 2,
                "city": "Chicago",
                "state": "IL",
                "items": {"name": "Ergonomic Office Chair", "price": 249.50, "qty": 1},
            },
            {
                "id": "ORD-99104",
                "txn_id": "TXN-PP-004",
                "customer": "Bob Martin",
                "email": "bob.m@example.com",
                "carrier": "FEDEX",
                "tracking": "TRK-FDX-556677",
                "days_ago": 5,
                "city": "Denver",
                "state": "CO",
                "items": {"name": "Dell 4K USB-C Monitor", "price": 380.00, "qty": 1},
            },
            {
                "id": "ORD-99105",
                "txn_id": "TXN-PP-005",
                "customer": "Elena Rostova",
                "email": "elena.r@example.com",
                "carrier": "UPS",
                "tracking": "TRK-UPS-112233",
                "days_ago": 3,
                "city": "Miami",
                "state": "FL",
                "items": {"name": "Mechanical Keyboard RGB", "price": 45.00, "qty": 1},
            },
        ]

        now = datetime.now(timezone.utc)
        for ord_data in sample_orders:
            res = await session.execute(select(MockOrder).where(MockOrder.id == ord_data["id"]))
            if not res.scalar_one_or_none():
                delivery_time = now - timedelta(days=ord_data["days_ago"])
                order = MockOrder(
                    id=ord_data["id"],
                    merchant_id=DEFAULT_MERCHANT_ID,
                    paypal_transaction_id=ord_data["txn_id"],
                    customer_name=ord_data["customer"],
                    customer_email=ord_data["email"],
                    shipping_carrier=ord_data["carrier"],
                    tracking_number=ord_data["tracking"],
                    delivery_status="DELIVERED",
                    delivery_timestamp=delivery_time,
                    item_details=ord_data["items"],
                )
                session.add(order)

            # Register with carrier tracking mock service
            carrier_service.register_tracking(
                tracking_number=ord_data["tracking"],
                carrier=ord_data["carrier"],
                status="DELIVERED",
                recipient_name=ord_data["customer"],
                delivery_days_ago=ord_data["days_ago"],
                destination_city=ord_data["city"],
                destination_state=ord_data["state"],
            )

        # 3. Seed Realistic Disputes & HITL Queue Items
        sample_disputes = [
            {
                "id": "PP-D-88219",
                "txn_id": "TXN-PP-001",
                "amount": Decimal("39.99"),
                "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
                "defense_status": "IN_HITL_REVIEW",
                "ai_conf": Decimal("0.94"),
                "ai_risk": "LOW",
                "summary": "Carrier tracking via FedEx confirms delivery 4 days ago to Austin, TX with signed POD. Delivery address matches order details. Recommended action: Submit delivery proof to PayPal.",
                "days_due": 3,
                "hitl_reason": "High confidence defense prepared; human confirmation requested prior to submission.",
            },
            {
                "id": "PP-D-99104",
                "txn_id": "TXN-PP-004",
                "amount": Decimal("380.00"),
                "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
                "defense_status": "IN_HITL_REVIEW",
                "ai_conf": Decimal("0.91"),
                "ai_risk": "LOW",
                "summary": "Dell 4K Monitor delivered via FedEx to Denver, CO. High claim amount ($380.00) exceeds merchant auto-submit threshold ($50.00). Deterministic policy triggers mandatory HITL approval.",
                "days_due": 5,
                "hitl_reason": "Claim amount ($380.00) exceeds merchant threshold ($50.00).",
            },
            {
                "id": "PP-D-77442",
                "txn_id": "TXN-PP-002",
                "amount": Decimal("1199.00"),
                "reason": "UNAUTHORISED",
                "defense_status": "SUBMITTED",
                "ai_conf": Decimal("0.88"),
                "ai_risk": "MEDIUM",
                "summary": "Order shipped via UPS to cardholder verified address with signature confirmation. Full evidence package successfully submitted to PayPal Resolution Center via POST /v1/customer/disputes/{id}/provide-evidence.",
                "days_due": 8,
                "hitl_reason": None,
            },
        ]

        for d_data in sample_disputes:
            d_res = await session.execute(select(Dispute).where(Dispute.id == d_data["id"]))
            if not d_res.scalar_one_or_none():
                dispute = Dispute(
                    id=d_data["id"],
                    merchant_id=DEFAULT_MERCHANT_ID,
                    disputed_transaction_id=d_data["txn_id"],
                    dispute_amount=d_data["amount"],
                    dispute_currency="USD",
                    reason=d_data["reason"],
                    status="WAITING_FOR_SELLER_RESPONSE",
                    lifecycle_stage="CLAIM",
                    seller_response_due_date=now + timedelta(days=d_data["days_due"]),
                    ai_confidence_score=d_data["ai_conf"],
                    ai_risk_level=d_data["ai_risk"],
                    ai_reasoning_summary=d_data["summary"],
                    defense_status=d_data["defense_status"],
                    raw_dispute_data={"seeded": True, "dispute_id": d_data["id"]},
                )
                session.add(dispute)
                await session.flush()

                # Add Order evidence
                session.add(
                    DisputeEvidence(
                        dispute_id=dispute.id,
                        evidence_type="PROOF_OF_FULFILLMENT",
                        provenance_source="INTERNAL_ORDER_DB",
                        source_reference_id=d_data["txn_id"],
                        content_summary=f"Order record {d_data['txn_id']} verified in merchant ERP.",
                        metadata_info={
                            "order_id": f"ORD-SEEDED-{d_data['id']}",
                            "customer_name": "Verified Buyer",
                            "customer_email": "buyer@example.com",
                        },
                    )
                )

                # Add Tracking evidence
                session.add(
                    DisputeEvidence(
                        dispute_id=dispute.id,
                        evidence_type="PROOF_OF_FULFILLMENT",
                        provenance_source="CARRIER_API",
                        source_reference_id=f"TRK-{d_data['id']}",
                        content_summary=f"Carrier tracking confirmed delivered by FEDEX.",
                        metadata_info={
                            "carrier": "FEDEX",
                            "tracking_number": f"TRK-{d_data['id']}",
                            "status": "DELIVERED",
                        },
                    )
                )

                if d_data["hitl_reason"]:
                    session.add(
                        HITLQueueItem(
                            dispute_id=dispute.id,
                            merchant_id=DEFAULT_MERCHANT_ID,
                            priority="HIGH",
                            trigger_reason="EXCEEDS_AMOUNT_THRESHOLD",
                            status="PENDING",
                        )
                    )

        # 4. Seed sample Invoices
        inv_res = await session.execute(select(Invoice).where(Invoice.merchant_id == DEFAULT_MERCHANT_ID))
        if not inv_res.scalars().first():
            inv1 = Invoice(
                merchant_id=DEFAULT_MERCHANT_ID,
                paypal_invoice_id="INV2-9A4B-2C8D-SANDBOX",
                invoice_number="INV-2026-001",
                recipient_name="Cyberdyne Systems AI",
                recipient_email="procurement@cyberdyne.com",
                currency="USD",
                total_amount=Decimal("1500.00"),
                payment_terms="DUE_ON_RECEIPT",
                status="SENT",
                confidence_score=Decimal("0.98"),
            )
            session.add(inv1)
            await session.flush()

            session.add(
                InvoiceLineItem(
                    invoice_id=inv1.id,
                    item_name="Neural Processor Calibration Cards",
                    description="Hardware tuning suite",
                    quantity=Decimal("2.00"),
                    unit_price=Decimal("750.00"),
                    tax_rate=Decimal("0.00"),
                    total=Decimal("1500.00"),
                )
            )

            inv2 = Invoice(
                merchant_id=DEFAULT_MERCHANT_ID,
                invoice_number="INV-2026-002",
                recipient_name="Stark Enterprises Logistics",
                recipient_email="ap@starkenterprises.com",
                currency="USD",
                total_amount=Decimal("2450.00"),
                payment_terms="NET_30",
                status="DRAFT",
                confidence_score=Decimal("0.95"),
            )
            session.add(inv2)
            await session.flush()

            session.add(
                InvoiceLineItem(
                    invoice_id=inv2.id,
                    item_name="High-Flux Arc Power Modules",
                    description="Industrial power components",
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("2450.00"),
                    tax_rate=Decimal("0.00"),
                    total=Decimal("2450.00"),
                )
            )

        # 5. Seed 7-Day Financial Snapshots for Cashflow Sentinel
        today = date.today()
        base_balance = Decimal("21000.00")
        for i in range(7, -1, -1):
            snap_date = today - timedelta(days=i)
            res = await session.execute(
                select(FinancialSnapshot).where(
                    FinancialSnapshot.merchant_id == DEFAULT_MERCHANT_ID,
                    FinancialSnapshot.snapshot_date == snap_date,
                )
            )
            if not res.scalar_one_or_none():
                daily_balance = base_balance + Decimal(f"{(7 - i) * 650}.00")
                snapshot = FinancialSnapshot(
                    merchant_id=DEFAULT_MERCHANT_ID,
                    snapshot_date=snap_date,
                    available_balance=daily_balance,
                    pending_balance=Decimal("1420.50"),
                    total_dispute_amount=Decimal("419.99"),
                    active_dispute_count=2,
                    dispute_rate_pct=Decimal("0.42"),
                    thirty_day_volume=Decimal("32400.00"),
                )
                session.add(snapshot)

        # 6. Seed sample Financial Alert
        alert_res = await session.execute(
            select(FinancialAlert).where(FinancialAlert.merchant_id == DEFAULT_MERCHANT_ID)
        )
        if not alert_res.scalars().first():
            alert = FinancialAlert(
                merchant_id=DEFAULT_MERCHANT_ID,
                alert_type="UPCOMING_DEADLINE",
                severity="WARNING",
                title="Dispute Response Deadline in 72 Hours",
                message="Dispute PP-D-88219 requires seller response within 72 hours to prevent default closure in buyer favor.",
                is_acknowledged=False,
            )
            session.add(alert)

        await session.commit()
        logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_data())
