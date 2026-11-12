import uuid
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.dispute import DisputeRead, DisputeEvidenceRead


class HITLAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor: str
    action: str
    previous_state: Dict[str, Any] | None
    new_state: Dict[str, Any] | None
    created_at: datetime


class HITLQueueItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dispute_id: str
    merchant_id: uuid.UUID
    priority: str
    trigger_reason: str
    status: str
    assigned_to: str | None
    created_at: datetime
    resolved_at: datetime | None
    dispute: DisputeRead | None = None
    audit_logs: List[HITLAuditLogRead] = []


class HITLActionDecision(BaseModel):
    decision: str = Field(..., description="APPROVE, APPROVE_SUBMISSION, REJECT, or CONCEDE")
    edited_notes: str | None = Field(default=None, description="Optional updated notes from merchant review")
    reviewer_notes: str | None = Field(default=None, description="Optional notes alias from frontend modal")
    actor: str = Field(default="MerchantAdmin", description="User identifying name or email")

