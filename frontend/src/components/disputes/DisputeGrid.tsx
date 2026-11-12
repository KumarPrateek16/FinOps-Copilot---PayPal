import React, { useState, useEffect, useMemo, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, ICellRendererParams } from 'ag-grid-community';
import { Dispute, HITLDecisionPayload } from '../../types';
import { disputesApi } from '../../services/api';
import { HITLReviewModal } from './HITLReviewModal';
import {
  Search,
  Clock,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

export const DisputeGrid: React.FC = () => {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedDispute, setSelectedDispute] = useState<Dispute | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const gridRef = useRef<AgGridReact>(null);

  const fetchDisputes = async () => {
    setLoading(true);
    try {
      const data = await disputesApi.list(statusFilter || undefined);
      setDisputes(data);
    } catch (err) {
      console.error('Failed to load disputes:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDisputes();
  }, [statusFilter]);

  const handleOpenReview = (dispute: Dispute) => {
    setSelectedDispute(dispute);
    setIsModalOpen(true);
  };

  const handleSubmitDecision = async (disputeId: string, payload: HITLDecisionPayload) => {
    await disputesApi.submitHITLAction(disputeId, payload);
    await fetchDisputes();
  };

  // AG Grid Column Definitions
  const colDefs = useMemo<ColDef<Dispute>[]>(() => [
    {
      headerName: 'Dispute ID',
      field: 'id',
      minWidth: 150,
      flex: 1,
      cellRenderer: (params: ICellRendererParams<Dispute>) => (
        <span className="font-mono text-xs font-bold text-slate-900">
          {params.value}
        </span>
      ),
    },
    {
      headerName: 'Transaction ID',
      field: 'disputed_transaction_id',
      minWidth: 150,
      flex: 1,
      cellRenderer: (params: ICellRendererParams<Dispute>) => (
        <span className="font-mono text-xs text-slate-500">{params.value}</span>
      ),
    },
    {
      headerName: 'Amount',
      field: 'dispute_amount',
      minWidth: 120,
      cellRenderer: (params: ICellRendererParams<Dispute>) => {
        const amt = Number(params.value || 0).toFixed(2);
        return (
          <span className="font-bold text-slate-900">
            ${amt} <span className="text-[10px] text-slate-400 font-normal">{params.data?.dispute_currency}</span>
          </span>
        );
      },
    },
    {
      headerName: 'Claim Reason',
      field: 'reason',
      minWidth: 200,
      flex: 1.5,
      cellRenderer: (params: ICellRendererParams<Dispute>) => {
        const label = (params.value || '').replace(/_/g, ' ');
        return (
          <span className="text-xs text-slate-700 truncate block font-medium" title={label}>
            {label}
          </span>
        );
      },
    },
    {
      headerName: 'Defense Status',
      field: 'defense_status',
      minWidth: 160,
      cellRenderer: (params: ICellRendererParams<Dispute>) => {
        const val = params.value;
        let badgeColor = 'bg-slate-100 text-slate-700 border-slate-200';
        if (val === 'SUBMITTED') badgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        else if (val === 'IN_HITL_REVIEW') badgeColor = 'bg-amber-50 text-amber-800 border-amber-200';
        else if (val === 'EVIDENCE_GATHERED') badgeColor = 'bg-blue-50 text-blue-700 border-blue-200';
        else if (val === 'CONCEDED') badgeColor = 'bg-rose-50 text-rose-700 border-rose-200';

        return (
          <span className={`px-2.5 py-0.5 rounded text-[11px] font-semibold border ${badgeColor}`}>
            {val}
          </span>
        );
      },
    },
    {
      headerName: 'AI Confidence',
      field: 'ai_confidence_score',
      minWidth: 130,
      cellRenderer: (params: ICellRendererParams<Dispute>) => {
        if (!params.value) return <span className="text-xs text-slate-400">N/A</span>;
        const pct = Math.round(Number(params.value) * 100);
        return (
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-slate-700" />
            <span className="text-xs font-bold text-slate-900">{pct}%</span>
          </div>
        );
      },
    },
    {
      headerName: 'Risk Level',
      field: 'ai_risk_level',
      minWidth: 110,
      cellRenderer: (params: ICellRendererParams<Dispute>) => {
        const lvl = params.value;
        if (!lvl) return <span className="text-xs text-slate-400">-</span>;
        const color =
          lvl === 'LOW'
            ? 'text-emerald-700 font-semibold'
            : lvl === 'MEDIUM'
            ? 'text-amber-800 font-semibold'
            : 'text-rose-700 font-bold';
        return <span className={`text-xs ${color}`}>{lvl}</span>;
      },
    },
    {
      headerName: 'Due Date',
      field: 'seller_response_due_date',
      minWidth: 130,
      cellRenderer: (params: ICellRendererParams<Dispute>) => {
        if (!params.value) return null;
        const date = new Date(params.value);
        return (
          <div className="flex items-center gap-1.5 text-xs text-slate-600 font-mono">
            <Clock className="w-3 h-3 text-slate-400" />
            <span>{date.toLocaleDateString()}</span>
          </div>
        );
      },
    },
    {
      headerName: 'Actions',
      minWidth: 120,
      cellRenderer: (params: ICellRendererParams<Dispute>) => {
        if (!params.data) return null;
        const isHitl = params.data.defense_status === 'IN_HITL_REVIEW';
        return (
          <button
            onClick={() => handleOpenReview(params.data!)}
            className={`rounded-md px-3 py-1 text-xs font-semibold transition shadow-sm cursor-pointer ${
              isHitl
                ? 'bg-slate-900 hover:bg-slate-800 text-white'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300'
            }`}
          >
            {isHitl ? 'Review' : 'View Details'}
          </button>
        );
      },
    },
  ], []);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
  }), []);

  return (
    <div className="space-y-3">
      {/* Search & Filter Bar - Minimalist Card */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 flex-1">
          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search disputes, transactions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-slate-800 transition"
            />
          </div>

          {/* Status Filter Buttons */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
            {['', 'IN_HITL_REVIEW', 'SUBMITTED', 'CONCEDED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap shrink-0 transition cursor-pointer ${
                  statusFilter === st
                    ? 'bg-slate-900 text-white'
                    : 'bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200'
                }`}
              >
                {st === '' ? 'All Disputes' : st.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Refresh Action */}
        <button
          onClick={fetchDisputes}
          disabled={loading}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 px-3.5 py-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 transition cursor-pointer self-start md:self-auto shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Row Click Hint */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-[11px] text-slate-500 px-1">
        <span className="leading-relaxed">
          Click any dispute row to inspect full case details, AI confidence scores, carrier tracking, and defense statements.
        </span>
        <span className="font-semibold text-slate-700 whitespace-nowrap shrink-0 self-start sm:self-auto bg-slate-100 sm:bg-transparent px-2 py-0.5 sm:p-0 rounded border border-slate-200 sm:border-0">
          {disputes.length} Total Disputes
        </span>
      </div>

      {/* Responsive AG Grid Container */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="ag-theme-alpine w-full" style={{ height: '520px' }}>
          <AgGridReact
            ref={gridRef}
            rowData={disputes}
            columnDefs={colDefs}
            defaultColDef={defaultColDef}
            pagination={true}
            paginationPageSize={10}
            quickFilterText={searchTerm}
            rowSelection="single"
            animateRows={true}
            onRowClicked={(event) => {
              if (event.data) {
                handleOpenReview(event.data);
              }
            }}
          />
        </div>
      </div>

      {/* HITL Review Modal */}
      <HITLReviewModal
        dispute={selectedDispute}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedDispute(null);
        }}
        onSubmitDecision={handleSubmitDecision}
      />
    </div>
  );
};
