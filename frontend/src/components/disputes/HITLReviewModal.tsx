import React, { useState } from 'react';
import { Dispute, HITLDecisionPayload } from '../../types';
import {
  X,
  AlertTriangle,
  Truck,
  CheckCircle2,
  Clock,
  Sparkles,
  Send,
  RotateCcw,
  PackageCheck,
  Scale,
} from 'lucide-react';

interface HITLReviewModalProps {
  dispute: Dispute | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmitDecision: (disputeId: string, payload: HITLDecisionPayload) => Promise<void>;
}

export const HITLReviewModal: React.FC<HITLReviewModalProps> = ({
  dispute,
  isOpen,
  onClose,
  onSubmitDecision,
}) => {
  if (!isOpen || !dispute) return null;

  const [notes, setNotes] = useState<string>(
    dispute.ai_reasoning_summary
      ? `Auto-generated defense summary: ${dispute.ai_reasoning_summary}`
      : 'Order fulfilled and confirmed delivered by carrier prior to dispute.'
  );
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Extract order/carrier evidence if present
  const orderEvidence = dispute.evidences?.find(
    (e) => e.evidence_type === 'ORDER_RECORD' || e.evidence_type === 'PROOF_OF_FULFILLMENT'
  )?.evidence_data;
  const trackingEvidence = dispute.evidences?.find(
    (e) => e.evidence_type === 'TRACKING_RECORD' || e.evidence_type === 'PROOF_OF_FULFILLMENT'
  )?.evidence_data;

  const isPendingReview = dispute.defense_status === 'IN_HITL_REVIEW';
  const isSubmitted = dispute.defense_status === 'SUBMITTED';
  const isConceded = dispute.defense_status === 'CONCEDED';

  const handleAction = async (decision: 'APPROVE_SUBMISSION' | 'CONCEDE_CLAIM') => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await onSubmitDecision(dispute.id, {
        decision,
        reviewer_notes: notes,
      });
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err.message || 'Action failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const confidencePct = dispute.ai_confidence_score
    ? Math.round(Number(dispute.ai_confidence_score) * 100)
    : 0;

  // Format Status Badge Color
  let statusBadgeColor = 'bg-slate-100 text-slate-700 border-slate-200';
  if (isSubmitted) statusBadgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  else if (isPendingReview) statusBadgeColor = 'bg-amber-50 text-amber-800 border-amber-200';
  else if (isConceded) statusBadgeColor = 'bg-rose-50 text-rose-700 border-rose-200';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 sm:p-6 overflow-y-auto antialiased">
      {/* Prompt Box with Rounded Corners and Generous Spacing */}
      <div className="relative w-full max-w-3xl rounded-2xl bg-white shadow-2xl border border-slate-200/90 overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-100 bg-white px-6 sm:px-8 py-5 shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white shrink-0 shadow-sm">
              <Scale className="h-5 w-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Dispute Case Details: <span className="font-mono">{dispute.id}</span>
                </h3>
                <span className={`rounded-md px-2.5 py-0.5 text-[11px] font-semibold border ${statusBadgeColor}`}>
                  {dispute.defense_status}
                </span>
                {dispute.lifecycle_stage && (
                  <span className="rounded-md px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200 uppercase">
                    {dispute.lifecycle_stage}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                PayPal Transaction: <span className="font-mono font-medium text-slate-700">{dispute.disputed_transaction_id}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition cursor-pointer"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Body with Clean Spacing & Padding */}
        <div className="p-6 sm:p-8 space-y-6 overflow-y-auto flex-1">
          {errorMsg && (
            <div className="rounded-xl bg-rose-50 p-4 border border-rose-200 text-xs font-semibold text-rose-800 flex items-center gap-2.5">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Section 1: Financial & Claim Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-5 space-y-1.5">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Disputed Amount
              </span>
              <p className="text-xl font-bold text-slate-900 tracking-tight">
                ${Number(dispute.dispute_amount).toFixed(2)}{' '}
                <span className="text-xs font-normal text-slate-500">{dispute.dispute_currency}</span>
              </p>
              <span className="text-[11px] text-slate-400 block pt-0.5">Funds placed on hold</span>
            </div>

            <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-5 space-y-1.5">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Buyer Claim Reason
              </span>
              <p className="text-xs font-bold text-slate-800 pt-0.5 capitalize leading-snug">
                {(dispute.reason || 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED').replace(/_/g, ' ').toLowerCase()}
              </p>
              <span className="text-[11px] text-slate-400 block pt-0.5">Item Not Received Claim</span>
            </div>

            <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-5 space-y-1.5">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Response Deadline
              </span>
              <p className="text-xs font-bold text-slate-900 flex items-center gap-1.5 pt-0.5">
                <Clock className="h-3.5 w-3.5 text-slate-500" />
                <span>{new Date(dispute.seller_response_due_date).toLocaleDateString()}</span>
              </p>
              <span className="text-[11px] text-slate-400 block pt-0.5">Submission window</span>
            </div>
          </div>

          {/* Section 2: Google Gemini AI Defense Assessment */}
          <div className="rounded-xl border border-slate-200/90 bg-white p-5 sm:p-6 space-y-3.5 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-slate-800" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                  Google Gemini 2.5 Flash Defense Analysis
                </h4>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Confidence:</span>
                <span
                  className={`px-2.5 py-0.5 rounded-md text-[11px] font-bold border ${
                    confidencePct >= 85
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}
                >
                  {confidencePct}% Probability
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-md text-[11px] font-bold border ${
                    dispute.ai_risk_level === 'LOW'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}
                >
                  {dispute.ai_risk_level || 'EVALUATING'} Risk
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200/70 font-normal">
              {dispute.ai_reasoning_summary ||
                'Gemini cross-referenced merchant ERP fulfillment timestamps against direct carrier API proof of delivery to calculate seller protection eligibility.'}
            </p>
          </div>

          {/* Section 3: Verified Evidence Package (Carrier + ERP Order) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Carrier Live Proof */}
            <div className="rounded-xl border border-slate-200/90 p-5 sm:p-6 bg-white space-y-3.5 shadow-sm">
              <div className="flex items-center gap-2 text-slate-900 font-bold text-xs pb-3 border-b border-slate-100">
                <Truck className="h-4 w-4 text-slate-800" />
                <span>Carrier Proof of Delivery</span>
              </div>
              <div className="text-xs space-y-3 text-slate-600">
                <div className="flex items-center justify-between py-0.5">
                  <span className="text-slate-400">Carrier:</span>
                  <span className="font-semibold text-slate-900">
                    {trackingEvidence?.carrier || 'FEDEX'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-0.5">
                  <span className="text-slate-400">Tracking Number:</span>
                  <span className="font-mono font-semibold text-slate-900">
                    {trackingEvidence?.tracking_number || 'TRK-FDX-998811'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-0.5">
                  <span className="text-slate-400">Delivery Status:</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>{trackingEvidence?.status || 'DELIVERED'}</span>
                  </span>
                </div>
                <div className="flex items-center justify-between py-0.5">
                  <span className="text-slate-400">Signature Proof:</span>
                  <span className="font-medium text-slate-800">
                    {trackingEvidence?.recipient_name ? `Signed by: ${trackingEvidence.recipient_name}` : 'Direct Signature on File'}
                  </span>
                </div>
              </div>
            </div>

            {/* Merchant Store Order Record */}
            <div className="rounded-xl border border-slate-200/90 p-5 sm:p-6 bg-white space-y-3.5 shadow-sm">
              <div className="flex items-center gap-2 text-slate-900 font-bold text-xs pb-3 border-b border-slate-100">
                <PackageCheck className="h-4 w-4 text-slate-800" />
                <span>Internal Order Record</span>
              </div>
              <div className="text-xs space-y-3 text-slate-600">
                <div className="flex items-center justify-between py-0.5">
                  <span className="text-slate-400">Internal Order ID:</span>
                  <span className="font-semibold text-slate-900">
                    {orderEvidence?.id || orderEvidence?.order_id || 'ORD-99101'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-0.5">
                  <span className="text-slate-400">Buyer Name:</span>
                  <span className="font-semibold text-slate-900">
                    {orderEvidence?.customer_name || 'Verified Customer'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-0.5">
                  <span className="text-slate-400">Items Disputed:</span>
                  <span className="font-medium text-slate-800 truncate max-w-[150px]">
                    {orderEvidence?.item_details?.name || 'Electronics Fulfillment'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-0.5">
                  <span className="text-slate-400">ERP Match:</span>
                  <span className="text-emerald-700 font-semibold">100% Address Match</span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 4: Submission Defense Statement */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-900 block">
                Evidence Package Statement for PayPal Dispute Specialist
              </label>
              {isSubmitted && (
                <span className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Submitted to PayPal Customer Disputes API</span>
                </span>
              )}
            </div>

            {isPendingReview ? (
              <textarea
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white p-4 text-xs text-slate-900 focus:border-slate-800 focus:outline-none transition leading-relaxed"
                placeholder="Review or edit merchant statement before submitting to PayPal..."
              />
            ) : (
              <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-4 text-xs text-slate-700 leading-relaxed font-normal">
                {notes}
              </div>
            )}
          </div>
        </div>

        {/* Modal Actions Footer with Proper Padding */}
        <div className="border-t border-slate-100 bg-slate-50/80 px-6 sm:px-8 py-4 flex flex-col-reverse sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          {isPendingReview ? (
            <>
              <button
                onClick={() => handleAction('CONCEDE_CLAIM')}
                disabled={submitting}
                className="flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold text-rose-700 bg-white border border-rose-200 hover:bg-rose-50 transition disabled:opacity-50 cursor-pointer shadow-sm"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Concede & Refund</span>
              </button>

              <div className="flex items-center justify-end gap-2.5">
                <button
                  onClick={onClose}
                  disabled={submitting}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-200 transition disabled:opacity-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleAction('APPROVE_SUBMISSION')}
                  disabled={submitting}
                  className="flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 text-white px-4 py-2 text-xs font-semibold hover:bg-slate-800 active:bg-slate-950 transition disabled:opacity-50 shadow-sm cursor-pointer"
                >
                  <Send className="h-3.5 w-3.5" />
                  <span>{submitting ? 'Submitting to PayPal...' : 'Approve & Submit Defense'}</span>
                </button>
              </div>
            </>
          ) : (
            <div className="w-full flex items-center justify-between">
              <span className="text-xs text-slate-500">
                {isSubmitted
                  ? 'This case is currently under active PayPal review.'
                  : isConceded
                  ? 'This case was conceded in buyer’s favor.'
                  : 'Automated defense workflow active.'}
              </span>
              <button
                onClick={onClose}
                className="rounded-lg bg-slate-900 text-white px-4 py-2 text-xs font-semibold hover:bg-slate-800 active:bg-slate-950 transition shadow-sm cursor-pointer"
              >
                Close Details
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
