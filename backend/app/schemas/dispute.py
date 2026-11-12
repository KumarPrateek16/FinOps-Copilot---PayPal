import uuid
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class DisputeEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dispute_id: str
    evidence_type: str
    provenance_source: str
    source_reference_id: str | None
    content_summary: str
    document_url: str | None
    metadata_info: Dict[str, Any]
    created_at: datetime


class DisputeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    merchant_id: uuid.UUID
    disputed_transaction_id: str
    dispute_amount: Decimal
    dispute_currency: str
    reason: str
    status: str
    lifecycle_stage: str
    seller_response_due_date: datetime
    ai_confidence_score: Decimal | None
    ai_risk_level: str | None
    ai_reasoning_summary: str | None
    defense_status: str
    created_at: datetime
    updated_at: datetime
    evidences: List[DisputeEvidenceRead] = []


class DisputeSubmissionRequest(BaseModel):
    action: str = Field(..., description="PROVIDE_EVIDENCE or ACCEPT_CLAIM")
    notes: str = Field(..., min_length=5, description="Evidence notes explaining merchant defense")
    carrier_name: str | None = None
    tracking_number: str | None = None

