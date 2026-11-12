import logging
from typing import Any, Dict
from fastapi import APIRouter, Header, Request, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.database.session import get_db
from app.models.webhook import WebhookEvent
from app.integrations.paypal.webhooks import PayPalWebhookVerifier
from app.workers.dispute_tasks import process_dispute_webhook_task

logger = logging.getLogger("webhook_router")
settings = get_settings()
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
webhook_verifier = PayPalWebhookVerifier()


@router.post("/paypal", status_code=status.HTTP_200_OK)
async def receive_paypal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    paypal_transmission_id: str | None = Header(None, alias="PAYPAL-TRANSMISSION-ID"),
    paypal_transmission_time: str | None = Header(None, alias="PAYPAL-TRANSMISSION-TIME"),
    paypal_cert_url: str | None = Header(None, alias="PAYPAL-CERT-URL"),
    paypal_auth_algo: str | None = Header(None, alias="PAYPAL-AUTH-ALGO"),
    paypal_transmission_sig: str | None = Header(None, alias="PAYPAL-TRANSMISSION-SIG"),
):
    """Receives and verifies PayPal webhook events with RSA-SHA256 signature verification and idempotency enforcement."""
    try:
        raw_payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )
    event_type = raw_payload.get("event_type", "UNKNOWN")

    # In local testing without PayPal simulator headers, allow test payloads if in debug mode
    if not paypal_transmission_id:
        if settings.APP_DEBUG:
            logger.warning("Debug mode: Missing transmission headers. Generating simulated transmission ID.")
            import uuid
            paypal_transmission_id = f"SIM-{uuid.uuid4()}"
            paypal_transmission_time = "2026-11-10T00:00:00Z"
            paypal_cert_url = "https://api-m.sandbox.paypal.com/v1/notifications/certs/CERT-SIMULATED"
            paypal_auth_algo = "SHA256withRSA"
            paypal_transmission_sig = "SIMULATED_SIG"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required PayPal transmission headers.",
            )

    logger.info("Received PayPal webhook event: %s (Transmission ID: %s)", event_type, paypal_transmission_id)

    # 1. Idempotency Check: Don't process duplicate events
    existing_query = select(WebhookEvent).where(WebhookEvent.paypal_transmission_id == paypal_transmission_id)
    result = await db.execute(existing_query)
    if result.scalar_one_or_none():
        logger.warning("Duplicate webhook transmission %s ignored.", paypal_transmission_id)
        return {"status": "duplicate_ignored", "transmission_id": paypal_transmission_id}

    # 2. Cryptographic Signature Verification
    webhook_id = settings.PAYPAL_WEBHOOK_ID or "SIMULATED_WEBHOOK_ID"
    is_valid = await webhook_verifier.verify_signature(
        transmission_id=paypal_transmission_id,
        transmission_time=paypal_transmission_time or "",
        cert_url=paypal_cert_url or "",
        auth_algo=paypal_auth_algo or "",
        transmission_sig=paypal_transmission_sig or "",
        webhook_id=webhook_id,
        raw_event=raw_payload,
    )

    if not is_valid:
        logger.error("Webhook signature verification failed for transmission %s", paypal_transmission_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PayPal webhook signature.",
        )

    # 3. Persist Event
    event_record = WebhookEvent(
        paypal_transmission_id=paypal_transmission_id,
        event_type=event_type,
        payload=raw_payload,
        verification_status="SUCCESS" if not paypal_transmission_id.startswith("SIM-") else "SIMULATED",
        processed_status="PENDING",
    )
    db.add(event_record)
    await db.commit()

    # 4. Asynchronously Dispatch to Celery Workers
    if event_type.startswith("CUSTOMER.DISPUTE."):
        logger.info("Dispatching dispute webhook task for %s", paypal_transmission_id)
        try:
            process_dispute_webhook_task.delay(paypal_transmission_id)
        except Exception as e:
            logger.warning("Celery dispatch deferred (worker may be offline in dev): %s", str(e))

    return {
        "status": "accepted",
        "event_type": event_type,
        "transmission_id": paypal_transmission_id,
    }

