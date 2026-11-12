from typing import Any, Dict
from pydantic import BaseModel, Field


class WebhookVerificationRequest(BaseModel):
    transmission_id: str = Field(..., description="PAYPAL-TRANSMISSION-ID header")
    transmission_time: str = Field(..., description="PAYPAL-TRANSMISSION-TIME header")
    cert_url: str = Field(..., description="PAYPAL-CERT-URL header")
    auth_algo: str = Field(..., description="PAYPAL-AUTH-ALGO header")
    transmission_sig: str = Field(..., description="PAYPAL-TRANSMISSION-SIG header")
    webhook_id: str
    webhook_event: Dict[str, Any]


class WebhookVerificationResponse(BaseModel):
    verification_status: str  # SUCCESS, FAILURE, SIMULATED
    message: str | None = None

