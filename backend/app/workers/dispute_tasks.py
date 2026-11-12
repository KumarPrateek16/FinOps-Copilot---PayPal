import logging
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from app.celery_app import celery_app
import app.database.session as db_session
from app.models.webhook import WebhookEvent
from app.models.dispute import Dispute
from app.agents.dispute_graph import dispute_agent_graph
from sqlalchemy import select

logger = logging.getLogger("dispute_worker")

DEFAULT_MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


async def _async_process_dispute_event(transmission_id: str):
    """Processes a dispute webhook event by executing the LangGraph dispute defense agent."""
    async with db_session.AsyncSessionLocal() as session:
        result = await session.execute(
            select(WebhookEvent).where(WebhookEvent.paypal_transmission_id == transmission_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            logger.error("Webhook event %s not found in database", transmission_id)
            return

        payload = event.payload
        resource = payload.get("resource", {})
        dispute_id = resource.get("dispute_id") or f"PP-D-{uuid.uuid4().hex[:8].upper()}"

        amount_dict = resource.get("dispute_amount", {})
        amount_val = float(amount_dict.get("value", 45.00))
        currency = amount_dict.get("currency_code", "USD")
        reason = resource.get("reason", "MERCHANDISE_OR_SERVICE_NOT_RECEIVED")
        due_date_str = resource.get("seller_response_due_date") or (
            datetime.now(timezone.utc) + timedelta(days=10)
        ).isoformat()

        txns = resource.get("disputed_transactions", [{}])
        txn_id = txns[0].get("seller_transaction_id", "TXN-PP-001")

        logger.info(
            "Worker initiating LangGraph dispute defense for %s (Amount: %s %s, Txn: %s)",
            dispute_id,
            amount_val,
            currency,
            txn_id,
        )

        # 1. Upsert dispute record in PostgreSQL
        res_disp = await session.execute(select(Dispute).where(Dispute.id == dispute_id))
        dispute = res_disp.scalar_one_or_none()
        if not dispute:
            dispute = Dispute(
                id=dispute_id,
                merchant_id=DEFAULT_MERCHANT_ID,
                disputed_transaction_id=txn_id,
                dispute_amount=Decimal(str(amount_val)),
                dispute_currency=currency,
                reason=reason,
                status="WAITING_FOR_SELLER_RESPONSE",
                lifecycle_stage=resource.get("dispute_life_cycle_stage", "INQUIRY"),
                seller_response_due_date=datetime.fromisoformat(due_date_str.replace("Z", "+00:00")),
                defense_status="INGESTED",
                raw_dispute_data=resource,
            )
            session.add(dispute)
            await session.commit()

        # 2. Invoke LangGraph agent with checkpoint thread_id
        config = {"configurable": {"thread_id": dispute_id}}
        initial_state = {
            "dispute_id": dispute_id,
            "merchant_id": str(DEFAULT_MERCHANT_ID),
            "transaction_id": txn_id,
            "amount": amount_val,
            "currency": currency,
            "reason": reason,
            "lifecycle_stage": resource.get("dispute_life_cycle_stage", "INQUIRY"),
            "due_date": due_date_str,
            "status": "WAITING_FOR_SELLER_RESPONSE",
        }

        try:
            agent_result = await dispute_agent_graph.ainvoke(initial_state, config=config)
            event.processed_status = "PROCESSED"
            await session.commit()
            logger.info("Dispute defense agent completed: status=%s", agent_result.get("submission_status"))
        except Exception as e:
            logger.error("Error executing dispute defense agent for %s: %s", dispute_id, str(e))
            event.processed_status = "FAILED"
            await session.commit()
            raise


@celery_app.task(bind=True, max_retries=3)
def process_dispute_webhook_task(self, transmission_id: str):
    """Celery task entry point for processing incoming PayPal dispute webhooks."""
    try:
        asyncio.run(_async_process_dispute_event(transmission_id))
    except Exception as exc:
        logger.warning("Retrying dispute webhook task for %s in 10s: %s", transmission_id, exc)
        raise self.retry(exc=exc, countdown=10)
