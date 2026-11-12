// Domain interfaces for PayPal FinOps Copilot

export type DefenseStatus =
  | 'INGESTED'
  | 'EVIDENCE_GATHERED'
  | 'IN_HITL_REVIEW'
  | 'SUBMITTED'
  | 'CONCEDED'
  | 'CLOSED';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface DisputeEvidence {
  id: string;
  evidence_type: string;
  source: string;
  source_id?: string;
  evidence_data: Record<string, any>;
  created_at: string;
}

export interface Dispute {
  id: string;
  merchant_id: string;
  disputed_transaction_id: string;
  dispute_amount: string | number;
  dispute_currency: string;
  reason: string;
  status: string;
  lifecycle_stage: string;
  seller_response_due_date: string;
  ai_confidence_score: number | null;
  ai_risk_level: RiskLevel | null;
  ai_reasoning_summary: string | null;
  defense_status: DefenseStatus;
  raw_dispute_data: Record<string, any>;
  created_at: string;
  updated_at: string;
  evidences: DisputeEvidence[];
}

export interface HITLQueueItem {
  id: string;
  dispute_id: string;
  reason_for_review: string;
  recommended_action: string;
  ai_notes: string;
  auto_submit_due_date?: string;
  status: 'PENDING' | 'APPROVED' | 'OVERRIDDEN' | 'CONCEDED';
  created_at: string;
}

export type HITLDecisionType = 'APPROVE_SUBMISSION' | 'OVERRIDE_RESPONSE' | 'CONCEDE_CLAIM';

export interface HITLDecisionPayload {
  decision: HITLDecisionType;
  reviewer_notes?: string;
  evidence_override?: Record<string, any>;
}

export interface InvoiceLineItem {
  id?: string;
  item_name: string;
  description?: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  total: number;
}

export interface Invoice {
  id: string;
  merchant_id: string;
  paypal_invoice_id: string | null;
  invoice_number: string;
  recipient_name: string;
  recipient_email: string;
  currency: string;
  total_amount: number;
  payment_terms: string;
  status: 'DRAFT' | 'SENT' | 'PAID' | 'CANCELLED';
  confidence_score: number | null;
  created_at: string;
  updated_at: string;
  line_items: InvoiceLineItem[];
}

export interface ExtractedInvoiceData {
  invoice_number: string;
  recipient_name: string;
  recipient_email: string;
  currency: string;
  payment_terms: string;
  line_items: InvoiceLineItem[];
  total_amount: number;
  confidence_score: number;
  notes?: string;
}

export interface FinancialSnapshot {
  id: string;
  snapshot_date: string;
  available_balance: number;
  pending_balance: number;
  total_dispute_amount: number;
  active_dispute_count: number;
  dispute_rate_pct: number;
  thirty_day_volume: number;
  created_at: string;
}

export interface FinancialAlert {
  id: string;
  alert_type: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  title: string;
  message: string;
  is_acknowledged: boolean;
  created_at: string;
}

export interface CashflowMetrics {
  available_balance: number;
  pending_balance: number;
  total_dispute_amount: number;
  active_dispute_count: number;
  dispute_rate_pct: number;
  thirty_day_volume: number;
  historical_snapshots: FinancialSnapshot[];
  active_alerts: FinancialAlert[];
  sync_source?: string;
  last_synced_at?: string;
}

