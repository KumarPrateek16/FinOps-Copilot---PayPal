import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MerchantBase(BaseModel):
    business_name: str = Field(..., max_length=255)
    paypal_payer_id: str = Field(..., max_length=64)
    hitl_auto_submit_threshold: Decimal = Field(default=Decimal("50.00"), ge=0)
    hitl_min_confidence_score: Decimal = Field(default=Decimal("0.85"), ge=0, le=1)


class MerchantCreate(MerchantBase):
    paypal_client_id: str
    paypal_client_secret: str
    webhook_id: str | None = None


class HITLSettingsUpdate(BaseModel):
    hitl_auto_submit_threshold: Decimal = Field(..., ge=0, description="Maximum amount for autonomous dispute submission")
    hitl_min_confidence_score: Decimal = Field(..., ge=0, le=1, description="Minimum AI confidence score for auto-defense")


class MerchantRead(MerchantBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    webhook_id: str | None
    created_at: datetime
    updated_at: datetime

