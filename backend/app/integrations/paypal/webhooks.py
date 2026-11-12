import logging
from typing import Any, Dict
from app.config import get_settings
from app.integrations.paypal.client import PayPalBaseClient

logger = logging.getLogger("paypal_webhooks")
settings = get_settings()


class PayPalWebhookVerifier:
    """Verifies incoming PayPal webhook authenticity against the official verify-webhook-signature API."""

    def __init__(self, client: PayPalBaseClient | None = None):
        self.client = client or PayPalBaseClient()

    async def verify_signature(
        self,
        transmission_id: str,
        transmission_time: str,
        cert_url: str,
        auth_algo: str,
        transmission_sig: str,
        webhook_id: str,
        raw_event: Dict[str, Any],
    ) -> bool:
        """Calls POST /v1/notifications/verify-webhook-signature to validate webhook authenticity.

        Returns True if verification_status == 'SUCCESS', False otherwise.
        """
        # In simulated / sandbox dev environments where simulator headers may be used
        if cert_url.startswith("https://api.sandbox.paypal.com") or cert_url.startswith("https://api-m.sandbox.paypal.com"):
            logger.debug("Verifying sandbox webhook signature...")

        payload = {
            "transmission_id": transmission_id,
            "transmission_time": transmission_time,
            "cert_url": cert_url,
            "auth_algo": auth_algo,
            "transmission_sig": transmission_sig,
            "webhook_id": webhook_id,
            "webhook_event": raw_event,
        }

        try:
            response = await self.client.request(
                method="POST",
                path="/v1/notifications/verify-webhook-signature",
                json_data=payload,
            )
            status = response.get("verification_status", "").upper()
            is_valid = status == "SUCCESS"
            if is_valid:
                logger.info("PayPal webhook verification succeeded for transmission %s", transmission_id)
            else:
                logger.warning(
                    "PayPal webhook verification rejected for transmission %s (status: %s)",
                    transmission_id,
                    status,
                )
            return is_valid
        except Exception as e:
            logger.error("Error verifying PayPal webhook signature: %s", str(e))
            # If in local development with simulated webhooks, allow fallback flag if configured
            if settings.APP_DEBUG and settings.APP_ENV == "development":
                logger.warning("Development mode: allowing simulated webhook signature verification.")
                return True
            return False
