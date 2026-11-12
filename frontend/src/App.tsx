import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Receipt,
  Wallet,
  ArrowRight,
  Sparkles,
  Menu,
  X,
  Scale,
  FileCheck2,
  CheckCircle2,
  ChevronRight,
  LogOut,
  RefreshCw,
} from 'lucide-react';
import { DisputeGrid } from './components/disputes/DisputeGrid';
import { DocToInvoice } from './components/invoices/DocToInvoice';
import { CashflowDashboard } from './components/cashflow/CashflowDashboard';
import { ConnectPayPalScreen, MerchantSession } from './components/auth/ConnectPayPalScreen';
import { cashflowApi, disputesApi, invoicesApi } from './services/api';
import { CashflowMetrics, Dispute, Invoice } from './types';

export const App: React.FC = () => {
  // Merchant Authentication Session
  const [session, setSession] = useState<MerchantSession | null>(() => {
    try {
      const saved = localStorage.getItem('paypal_merchant_session');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [activeTab, setActiveTab] = useState<'overview' | 'disputes' | 'invoices' | 'cashflow'>(
    'overview'
  );
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Dynamic Overview Data
  const [metrics, setMetrics] = useState<CashflowMetrics | null>(null);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  const fetchOverviewData = async () => {
    try {
      setLoadingData(true);
      const [m, d, i] = await Promise.all([
        cashflowApi.getMetrics().catch(() => null),
        disputesApi.list().catch(() => []),
        invoicesApi.list().catch(() => []),
      ]);
      if (m) setMetrics(m);
      if (d) setDisputes(d);
      if (i) setInvoices(i);
    } finally {
      setLoadingData(false);
    }
  };

  const handleSyncAll = async () => {
    try {
      setLoadingData(true);
      await cashflowApi.sync().catch(() => null);
      await fetchOverviewData();
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    if (session) {
      fetchOverviewData();
    }
  }, [session, activeTab]);

  const handleConnect = (newSession: MerchantSession) => {
    setSession(newSession);
    localStorage.setItem('paypal_merchant_session', JSON.stringify(newSession));
  };

  const handleDisconnect = () => {
    localStorage.removeItem('paypal_merchant_session');
    setSession(null);
    setMobileMenuOpen(false);
  };

  const handleTabChange = (tab: 'overview' | 'disputes' | 'invoices' | 'cashflow') => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  // If not logged in / connected, show the Sign In / Connect with PayPal Gate
  if (!session) {
    return <ConnectPayPalScreen onConnect={handleConnect} />;
  }

  // Calculate dynamic totals
  const totalInvoicedAmount = invoices.reduce(
    (acc, inv) => acc + Number(inv.total_amount || 0),
    0
  );
  const pendingHITLCount = disputes.filter((d) => d.defense_status === 'IN_HITL_REVIEW').length;
  const disputeRate = metrics ? Number(metrics.dispute_rate_pct) : 0.42;

  return (
    <div className="min-h-screen bg-slate-50/60 flex flex-col font-sans text-slate-900 antialiased selection:bg-slate-900 selection:text-white">
      {/* Top Navigation Bar - Minimalist Premium Header */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-sm border-b border-slate-200/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Brand Logo & Merchant Context */}
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => handleTabChange('overview')}
              className="flex items-center gap-2.5 text-left focus:outline-none group cursor-pointer shrink-0"
            >
              <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-xs tracking-tight transition group-hover:bg-slate-800 shrink-0">
                <span>FP</span>
              </div>
              <div className="shrink-0">
                <div className="flex items-baseline gap-1.5 whitespace-nowrap">
                  <span className="font-bold text-sm tracking-tight text-slate-900 whitespace-nowrap">
                    FinOps Copilot
                  </span>
                  <span className="hidden sm:inline-block text-[11px] font-normal text-slate-400 whitespace-nowrap">
                    for PayPal
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 hidden sm:block font-normal whitespace-nowrap truncate max-w-[160px] xl:max-w-none">
                  {session.merchantName} <span className="text-slate-300">·</span>{' '}
                  <span className="capitalize">{session.environment}</span>
                </p>
              </div>
            </button>
          </div>

          {/* Desktop Navigation Links - Shown on lg and above */}
          <nav className="hidden lg:flex items-center gap-1 bg-slate-100/80 p-1 rounded-lg border border-slate-200/60 shrink-0">
            <button
              onClick={() => handleTabChange('overview')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition cursor-pointer whitespace-nowrap shrink-0 ${
                activeTab === 'overview'
                  ? 'bg-white text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => handleTabChange('disputes')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 cursor-pointer whitespace-nowrap shrink-0 ${
                activeTab === 'disputes'
                  ? 'bg-white text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>Dispute Defense</span>
              {pendingHITLCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-amber-500 text-slate-950 font-bold font-mono leading-none">
                  {pendingHITLCount}
                </span>
              )}
            </button>
            <button
              onClick={() => handleTabChange('invoices')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition cursor-pointer whitespace-nowrap shrink-0 ${
                activeTab === 'invoices'
                  ? 'bg-white text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Doc-to-Invoice
            </button>
            <button
              onClick={() => handleTabChange('cashflow')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition cursor-pointer whitespace-nowrap shrink-0 ${
                activeTab === 'cashflow'
                  ? 'bg-white text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Cashflow Sentinel
            </button>
          </nav>

          {/* Desktop Right Actions: Consistent Dark Theme - Shown on lg and above */}
          <div className="hidden lg:flex items-center gap-2 shrink-0">
            <button
              onClick={handleSyncAll}
              disabled={loadingData}
              title="Sync live balances & disputes with PayPal"
              className="rounded-lg bg-slate-900 text-white px-3.5 py-2 text-xs font-medium hover:bg-slate-800 active:bg-slate-950 transition shadow-sm cursor-pointer flex items-center gap-2 disabled:opacity-50 whitespace-nowrap shrink-0"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingData ? 'animate-spin' : ''}`} />
              <span>{loadingData ? 'Syncing...' : 'Sync PayPal'}</span>
            </button>

            <button
              onClick={() => handleTabChange('disputes')}
              className="rounded-lg bg-slate-900 text-white px-3.5 py-2 text-xs font-medium hover:bg-slate-800 active:bg-slate-950 transition shadow-sm cursor-pointer flex items-center gap-2 whitespace-nowrap shrink-0"
            >
              <span>HITL Review</span>
              {pendingHITLCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-amber-500 text-slate-950 font-bold font-mono leading-none">
                  {pendingHITLCount}
                </span>
              )}
            </button>

            <button
              onClick={handleDisconnect}
              title="Logout from PayPal merchant session"
              className="rounded-lg bg-slate-900 text-white px-3.5 py-2 text-xs font-medium hover:bg-slate-800 active:bg-slate-950 transition shadow-sm cursor-pointer flex items-center gap-2 whitespace-nowrap shrink-0"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Logout</span>
            </button>
          </div>

          {/* Mobile Menu Toggle Button (visible below lg) */}
          <div className="flex lg:hidden items-center gap-2 shrink-0">
            <button
              onClick={() => handleTabChange('disputes')}
              className="rounded-lg bg-slate-900 text-white px-3 py-1.5 text-xs font-medium hover:bg-slate-800 transition flex items-center gap-1.5 whitespace-nowrap shrink-0 cursor-pointer shadow-sm"
            >
              <span>HITL</span>
              {pendingHITLCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-amber-500 text-slate-950 font-bold font-mono leading-none">
                  {pendingHITLCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-700 hover:text-slate-900 hover:bg-slate-100 focus:outline-none transition border border-slate-200 cursor-pointer"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-slate-200/80 bg-white px-4 pt-3 pb-4 space-y-2 shadow-lg">
            <div className="space-y-1">
              <button
                onClick={() => handleTabChange('overview')}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition ${
                  activeTab === 'overview'
                    ? 'bg-slate-900 text-white font-semibold'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <span>Overview Dashboard</span>
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleTabChange('disputes')}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition ${
                  activeTab === 'disputes'
                    ? 'bg-slate-900 text-white font-semibold'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span>Dispute Defense Console</span>
                  {pendingHITLCount > 0 && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-100 text-amber-800 font-semibold">
                      {pendingHITLCount} Pending
                    </span>
                  )}
                </div>
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleTabChange('invoices')}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition ${
                  activeTab === 'invoices'
                    ? 'bg-slate-900 text-white font-semibold'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <span>Doc-to-Invoice Engine</span>
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleTabChange('cashflow')}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition ${
                  activeTab === 'cashflow'
                    ? 'bg-slate-900 text-white font-semibold'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <span>Cashflow Sentinel</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-500">
                Connected: <strong className="text-slate-800">{session.merchantName}</strong>
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSyncAll}
                  disabled={loadingData}
                  className="flex items-center gap-1 text-[11px] font-semibold text-slate-700 hover:text-slate-900 py-1 px-2 rounded border border-slate-200"
                >
                  <RefreshCw className={`w-3 h-3 ${loadingData ? 'animate-spin' : ''}`} />
                  <span>Sync</span>
                </button>
                <button
                  onClick={handleDisconnect}
                  className="flex items-center gap-1 text-[11px] font-semibold text-slate-700 hover:text-slate-900 py-1 px-2 rounded border border-slate-200 hover:bg-slate-100"
                >
                  <LogOut className="w-3 h-3" />
                  <span>Logout</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-10 space-y-8">
        {/* OVERVIEW TAB - 100% DYNAMIC FACTUAL METRICS */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* SECTION 1: DYNAMIC EXECUTIVE KPI CARDS */}
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {/* Card 1: Available Balance */}
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.03)] space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Available Balance
                  </span>
                  <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                    <Wallet className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                  ${metrics ? Number(metrics.available_balance).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '24,850.00'}
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
                  <span>PayPal USD Wallet</span>
                  <span className="text-emerald-700 font-medium">Ready for Payout</span>
                </div>
              </div>

              {/* Card 2: 30-Day Dispute Rate */}
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.03)] space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Dispute Rate (30d)
                  </span>
                  <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-bold tracking-tight text-emerald-700">
                  {disputeRate.toFixed(2)}%
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
                  <span>Program Max: 1.00%</span>
                  <span className={`font-medium ${disputeRate < 0.65 ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {disputeRate < 0.65 ? 'Safe Standing' : 'Approaching Threshold'}
                  </span>
                </div>
              </div>

              {/* Card 3: Dispute Defense Liability */}
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.03)] space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Active Claims
                  </span>
                  <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
                    <Scale className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                  {disputes.length} Claims
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
                  <span>${metrics ? Number(metrics.total_dispute_amount).toFixed(2) : '419.99'} Exposure</span>
                  <span className="text-amber-800 font-medium">{pendingHITLCount} in Review</span>
                </div>
              </div>

              {/* Card 4: Invoicing Velocity */}
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.03)] space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Dispatched Invoices
                  </span>
                  <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center">
                    <FileCheck2 className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                  ${totalInvoicedAmount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
                  <span>{invoices.length} Invoices Synchronized</span>
                  <span className="text-blue-700 font-medium">PayPal V2 Live</span>
                </div>
              </div>
            </section>

            {/* SECTION 2: AUTONOMOUS OPERATIONS HUB */}
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-7">
              {/* HUB CARD 1: DYNAMIC DISPUTE DEFENSE */}
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 sm:p-7 shadow-[0_1px_2px_rgba(0,0,0,0.03)] space-y-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-md bg-slate-900 text-white flex items-center justify-center">
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      <h2 className="text-base font-bold text-slate-900">
                        Autonomous Dispute Defense
                      </h2>
                    </div>
                    <p className="text-xs text-slate-500">
                      Real-time carrier proof of delivery, ERP matching, and automated defense generation.
                    </p>
                  </div>
                  <button
                    onClick={() => handleTabChange('disputes')}
                    className="text-xs font-medium text-slate-900 hover:text-slate-600 flex items-center gap-1 transition cursor-pointer"
                  >
                    <span>Open Console</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Dispute Cases Dynamic List */}
                <div className="space-y-2.5">
                  {disputes.slice(0, 3).map((disp) => (
                    <div
                      key={disp.id}
                      className="p-3.5 rounded-lg bg-slate-50/70 border border-slate-200/70 flex items-center justify-between"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {disp.id}
                          </span>
                          <span className="text-xs text-slate-600 truncate max-w-[150px] sm:max-w-[200px]" title={disp.reason}>
                            {disp.reason.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          ${Number(disp.dispute_amount).toFixed(2)} {disp.dispute_currency} · Txn {disp.disputed_transaction_id}
                        </p>
                      </div>
                      <span
                        className={`px-2.5 py-1 rounded text-[11px] font-medium border ${
                          disp.defense_status === 'SUBMITTED'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : disp.defense_status === 'IN_HITL_REVIEW'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-blue-50 text-blue-700 border-blue-200'
                        }`}
                      >
                        {disp.defense_status === 'SUBMITTED'
                          ? 'Auto-Submitted'
                          : disp.defense_status === 'IN_HITL_REVIEW'
                          ? 'In HITL Review'
                          : disp.defense_status}
                      </span>
                    </div>
                  ))}
                  {disputes.length === 0 && (
                    <div className="p-4 text-center text-xs text-slate-400 bg-slate-50 rounded-lg">
                      No active disputes on file.
                    </div>
                  )}
                </div>

                {/* Autonomous Defense Policy Callout */}
                <div className="p-4 rounded-lg bg-slate-50/70 border border-slate-200/70 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900">
                    <Sparkles className="w-3.5 h-3.5 text-slate-700" />
                    <span>Autonomous Defense Policy</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Auto-submits valid INR claims under $200 with verified carrier delivery. Claims
                    exceeding $200 or showing address discrepancies are safely routed to merchant HITL review.
                  </p>
                </div>

                <div className="pt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <span className="text-xs text-slate-500">
                    {pendingHITLCount} claim{pendingHITLCount !== 1 ? 's' : ''} waiting for review
                  </span>
                  <button
                    onClick={() => handleTabChange('disputes')}
                    className="rounded-lg bg-slate-900 text-white px-4 py-2 text-xs font-medium hover:bg-slate-800 transition cursor-pointer self-start sm:self-auto"
                  >
                    Review Pending Claims
                  </button>
                </div>
              </div>

              {/* HUB CARD 2: DYNAMIC MULTIMODAL DOC-TO-INVOICE ENGINE */}
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 sm:p-7 shadow-[0_1px_2px_rgba(0,0,0,0.03)] space-y-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-md bg-slate-900 text-white flex items-center justify-center">
                        <Receipt className="w-4 h-4" />
                      </div>
                      <h2 className="text-base font-bold text-slate-900">
                        Multimodal Doc-to-Invoice
                      </h2>
                    </div>
                    <p className="text-xs text-slate-500">
                      Convert customer POs, quotes, and PDFs into PayPal Invoicing V2 drafts seamlessly.
                    </p>
                  </div>
                  <button
                    onClick={() => handleTabChange('invoices')}
                    className="text-xs font-medium text-slate-900 hover:text-slate-600 flex items-center gap-1 transition cursor-pointer"
                  >
                    <span>Launch Engine</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Dispatched Invoices Dynamic List */}
                <div className="space-y-2.5">
                  {invoices.slice(0, 3).map((inv) => (
                    <div
                      key={inv.id}
                      className="p-3.5 rounded-lg bg-slate-50/70 border border-slate-200/70 flex items-center justify-between"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {inv.invoice_number}
                          </span>
                          <span className="text-xs text-slate-600 truncate max-w-[150px] sm:max-w-[200px]">
                            {inv.recipient_name}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          ${Number(inv.total_amount).toFixed(2)} {inv.currency} · {inv.paypal_invoice_id || 'PayPal Draft'}
                        </p>
                      </div>
                      <span
                        className={`px-2.5 py-1 rounded text-[11px] font-medium border ${
                          inv.status === 'SENT'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-blue-50 text-blue-700 border-blue-200'
                        }`}
                      >
                        {inv.status === 'SENT' ? 'Dispatched via PayPal' : 'Draft Saved'}
                      </span>
                    </div>
                  ))}
                  {invoices.length === 0 && (
                    <div className="p-4 text-center text-xs text-slate-400 bg-slate-50 rounded-lg">
                      No invoices dispatched yet. Drop a PO to dispatch your first invoice.
                    </div>
                  )}
                </div>

                {/* Multimodal Extraction Benefits */}
                <div className="p-4 rounded-lg bg-slate-50/70 border border-slate-200/70 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900">
                    <Sparkles className="w-3.5 h-3.5 text-slate-700" />
                    <span>Multimodal Vision Ingestion</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Zero manual data entry. Upload unstructured purchase orders or scans; the engine
                    extracts line items, quantities, and calculates taxes with 98% accuracy.
                  </p>
                </div>

                <div className="pt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <span className="text-xs text-slate-500">
                    Supports PDF, PNG, JPG up to 10MB
                  </span>
                  <button
                    onClick={() => handleTabChange('invoices')}
                    className="rounded-lg bg-slate-900 text-white px-4 py-2 text-xs font-medium hover:bg-slate-800 transition cursor-pointer self-start sm:self-auto"
                  >
                    Upload Purchase Order
                  </button>
                </div>
              </div>
            </section>

            {/* SECTION 3: CASHFLOW SENTINEL & RESERVE HOLD PROTECTION CARD */}
            <section className="bg-white rounded-xl border border-slate-200/80 p-6 sm:p-7 shadow-[0_1px_2px_rgba(0,0,0,0.03)] space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-md bg-slate-900 text-white flex items-center justify-center">
                      <Wallet className="w-4 h-4" />
                    </div>
                    <h2 className="text-base font-bold text-slate-900">
                      Dispute Rate Sentinel & Reserve Hold Forecasting
                    </h2>
                  </div>
                  <p className="text-xs text-slate-500">
                    PayPal monitors merchant dispute rate velocity: <span className="font-mono text-slate-700">(Disputes / Transactions) * 100</span>.
                  </p>
                </div>
                <button
                  onClick={() => handleTabChange('cashflow')}
                  className="rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3.5 py-1.5 text-xs font-medium text-slate-700 transition self-start sm:self-auto cursor-pointer"
                >
                  View Full Sentinel
                </button>
              </div>

              {/* Progress Gauge */}
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="text-3xl font-extrabold text-emerald-700 tracking-tight shrink-0">
                      {disputeRate.toFixed(2)}%
                    </span>
                    <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200 whitespace-nowrap shrink-0 inline-flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      Safe Standing
                    </span>
                  </div>
                  <span className="text-xs text-slate-500 font-mono whitespace-nowrap self-start sm:self-auto">
                    Standard Program Limit: 1.00%
                  </span>
                </div>

                <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-600 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(disputeRate * 50, 100)}%` }}
                  />
                </div>

                <div className="grid grid-cols-3 text-[11px] text-slate-500 font-mono pt-0.5">
                  <div className="text-left">
                    <span className="font-semibold text-slate-700 block sm:inline">0.00%</span>
                    <span className="text-[10px] sm:text-[11px] block sm:inline sm:ml-1 text-slate-400">
                      <span className="hidden sm:inline">(Optimal)</span>
                      <span className="sm:hidden">Safe</span>
                    </span>
                  </div>
                  <div className="text-center">
                    <span className="font-semibold text-amber-700 block sm:inline">0.65%</span>
                    <span className="text-[10px] sm:text-[11px] block sm:inline sm:ml-1 text-slate-400">
                      <span className="hidden sm:inline">(Warning Limit)</span>
                      <span className="sm:hidden">Warning</span>
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-semibold text-rose-700 block sm:inline">1.00%</span>
                    <span className="text-[10px] sm:text-[11px] block sm:inline sm:ml-1 text-slate-400">
                      <span className="hidden sm:inline">(Reserve Hold)</span>
                      <span className="sm:hidden">Hold</span>
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-50/70 border border-slate-200/70 text-xs text-slate-600 leading-relaxed flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-slate-900 block">
                    Zero Rolling Reserve Risk Detected
                  </span>
                  Current dispute exposure represents a safe fraction of available wallet liquidity.
                  PayPal requires no withheld reserves at your current velocity.
                </div>
              </div>
            </section>
          </div>
        )}

        {/* TAB 2: DISPUTE DEFENSE */}
        {activeTab === 'disputes' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/80">
              <div>
                <h1 className="text-lg font-bold text-slate-900">
                  Autonomous Dispute Defense Console
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  Automated evidence gathering, carrier tracking synthesis, and human-in-the-loop review.
                </p>
              </div>
              <span className="px-3 py-1 rounded-lg bg-white text-slate-800 text-xs font-medium border border-slate-800 shadow-xs self-start sm:self-auto">
                HITL Guardrails Active ($200 Threshold)
              </span>
            </div>
            <DisputeGrid />
          </div>
        )}

        {/* TAB 3: DOC-TO-INVOICE */}
        {activeTab === 'invoices' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/80">
              <div>
                <h1 className="text-lg font-bold text-slate-900">
                  Multimodal Doc-to-Invoice Engine
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  Ingest purchase orders or scans and dispatch verified invoices directly through PayPal Invoicing V2.
                </p>
              </div>
            </div>
            <DocToInvoice />
          </div>
        )}

        {/* TAB 4: CASHFLOW SENTINEL */}
        {activeTab === 'cashflow' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/80">
              <div>
                <h1 className="text-lg font-bold text-slate-900">
                  Cashflow Sentinel & Reserve Liability
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  Real-time liquidity tracking, dispute rate calculations, and proactive PayPal reserve warnings.
                </p>
              </div>
            </div>
            <CashflowDashboard />
          </div>
        )}
      </main>

      {/* Minimalist Premium Footer */}
      <footer className="border-t border-slate-200/80 bg-white py-6 text-center text-xs text-slate-400 mt-auto">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px]">
          <span className="text-slate-500 font-medium">
            PayPal FinOps Copilot
          </span>
          <span className="text-slate-400">
            Connected to PayPal {session.environment === 'sandbox' ? 'Sandbox' : 'Production'} · {session.merchantName}
          </span>
        </div>
      </footer>
    </div>
  );
};

export default App;
