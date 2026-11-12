import pytest
import uuid
from decimal import Decimal
from httpx import AsyncClient
from tests.conftest import TestingSessionLocal
from app.models.merchant import Merchant
from app.models.cashflow import MockOrder
from app.integrations.shipping.carrier_mock import carrier_service
from app.agents.dispute_graph import build_dispute_agent_graph
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

TEST_MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture(autouse=True)
async def seed_test_merchant_and_order(setup_test_db):
    """Seeds test merchant and order in the test database."""
    async with TestingSessionLocal() as session:
        merchant = Merchant(
            id=TEST_MERCHANT_ID,
            business_name="Test Merchant",
            paypal_payer_id="PAYER-TEST-001",
            paypal_client_id="client_test",
            paypal_client_secret_enc=b"enc",
            hitl_auto_submit_threshold=Decimal("50.00"),
            hitl_min_confidence_score=Decimal("0.85"),
        )
        session.add(merchant)

        order = MockOrder(
            id="ORD-TEST-100",
            merchant_id=TEST_MERCHANT_ID,
            paypal_transaction_id="TXN-TEST-100",
            customer_name="John Doe",
            customer_email="john@example.com",
            shipping_carrier="FEDEX",
            tracking_number="TRK-TEST-DELIV-100",
            delivery_status="DELIVERED",
            item_details={"item": "Widget", "price": 40.00},
        )
        session.add(order)
        await session.commit()

    carrier_service.register_tracking(
        tracking_number="TRK-TEST-DELIV-100",
        carrier="FEDEX",
        status="DELIVERED",
        recipient_name="John Doe",
        delivery_days_ago=4,
    )


@pytest.mark.asyncio
async def test_dispute_agent_autonomous_defense():
    """Test Case 1: Dispute under threshold ($40 <= $50) with verified delivery.

    Must auto-submit without requiring HITL review.
    """
    graph = build_dispute_agent_graph(checkpointer=MemorySaver())
    dispute_id = "PP-D-AUTO-001"

    initial_state = {
        "dispute_id": dispute_id,
        "merchant_id": str(TEST_MERCHANT_ID),
        "transaction_id": "TXN-TEST-100",
        "amount": 40.00,
        "currency": "USD",
        "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
        "lifecycle_stage": "INQUIRY",
        "due_date": "2026-11-20T00:00:00Z",
        "status": "WAITING_FOR_SELLER_RESPONSE",
    }

    config = {"configurable": {"thread_id": dispute_id}}
    final_state = await graph.ainvoke(initial_state, config=config)

    # Assertions
    assert final_state["requires_hitl"] is False
    assert final_state["confidence_score"] >= 0.85
    assert final_state["submission_status"] == "SUBMITTED"
    assert "Delivered" in final_state["proposed_notes"] or "delivered" in final_state["proposed_notes"]


@pytest.mark.asyncio
async def test_dispute_agent_hitl_interrupt_and_resume():
    """Test Case 2: Dispute over threshold ($250 > $50).

    Must pause at hitl_checkpoint, then resume upon human approval.
    """
    graph = build_dispute_agent_graph(checkpointer=MemorySaver())
    dispute_id = "PP-D-HITL-002"

    initial_state = {
        "dispute_id": dispute_id,
        "merchant_id": str(TEST_MERCHANT_ID),
        "transaction_id": "TXN-TEST-100",
        "amount": 250.00,  # Exceeds threshold
        "currency": "USD",
        "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
        "lifecycle_stage": "INQUIRY",
        "due_date": "2026-11-20T00:00:00Z",
        "status": "WAITING_FOR_SELLER_RESPONSE",
    }

    config = {"configurable": {"thread_id": dispute_id}}

    # 1. First run halts at interrupt
    paused_state = await graph.ainvoke(initial_state, config=config)

    # Verify that the graph paused and flagged HITL requirement
    assert paused_state["requires_hitl"] is True
    assert "exceeds auto-submit limit" in paused_state["hitl_trigger_reason"]

    # 2. Simulate merchant reviewing and editing the response notes
    resumed_state = await graph.ainvoke(
        Command(resume={
            "action": "EDIT_AND_APPROVE",
            "edited_notes": "Reviewed by store manager: FedEx tracking confirms signature delivery.",
            "actor": "StoreManager",
        }),
        config=config,
    )

    # 3. Verify successful resumption and defense submission
    assert resumed_state["submission_status"] == "SUBMITTED"
    assert resumed_state["human_action"] == "EDIT_AND_APPROVE"
    assert "Reviewed by store manager" in resumed_state["human_edited_notes"]


@pytest.mark.asyncio
async def test_dispute_agent_concede_flow():
    """Test Case 3: Merchant decides to concede and refund claim."""
    graph = build_dispute_agent_graph(checkpointer=MemorySaver())
    dispute_id = "PP-D-CONCEDE-003"

    initial_state = {
        "dispute_id": dispute_id,
        "merchant_id": str(TEST_MERCHANT_ID),
        "transaction_id": "TXN-TEST-100",
        "amount": 150.00,
        "currency": "USD",
        "reason": "SIGNIFICANTLY_NOT_AS_DESCRIBED",
        "lifecycle_stage": "INQUIRY",
        "due_date": "2026-11-20T00:00:00Z",
        "status": "WAITING_FOR_SELLER_RESPONSE",
    }

    config = {"configurable": {"thread_id": dispute_id}}

    # Pause at HITL
    await graph.ainvoke(initial_state, config=config)

    # Concede
    resumed = await graph.ainvoke(
        Command(resume={"action": "CONCEDE", "actor": "SupportLead"}),
        config=config,
    )

    assert resumed["submission_status"] == "CONCEDED"
    assert resumed["human_action"] == "CONCEDE"
