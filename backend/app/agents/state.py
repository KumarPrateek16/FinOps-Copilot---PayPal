from typing import TypedDict, Optional, List, Dict, Any


class DisputeState(TypedDict):
    """Complete state representation for the Autonomous Dispute Defense LangGraph agent."""

    dispute_id: str
    merchant_id: str
    transaction_id: str
    amount: float
    currency: str
    reason: str
    lifecycle_stage: str
    due_date: str
    status: str

    # Evidence & Provenance Aggregation
    gathered_evidences: List[Dict[str, Any]]
    carrier_tracking_info: Optional[Dict[str, Any]]
    order_history: Optional[Dict[str, Any]]

    # AI Synthesis & Assessment
    confidence_score: float
    risk_level: str  # LOW, MEDIUM, HIGH
    ai_reasoning: str
    proposed_notes: str
    proposed_evidence_type: str

    # Policy Engine & Guardrails
    requires_hitl: bool
    hitl_trigger_reason: Optional[str]

    # Human-in-the-Loop Review (Resumed via Command)
    human_action: Optional[str]  # APPROVE, REJECT, CONCEDE, EDIT_AND_APPROVE
    human_edited_notes: Optional[str]
    actor: Optional[str]

    # Final Outcome
    submission_status: str  # PENDING, SUBMITTED, CONCEDED, REJECTED, FAILED
    submission_response: Optional[Dict[str, Any]]
    error: Optional[str]

