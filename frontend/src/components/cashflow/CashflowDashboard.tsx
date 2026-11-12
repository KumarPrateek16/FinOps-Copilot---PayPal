import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  Wallet,
  Clock,
  RefreshCw,
  ArrowUpRight,
  ShieldCheck,
  CheckCircle2,
  Zap,
} from 'lucide-react';
import { CashflowMetrics } from '../../types';
import { cashflowApi } from '../../services/api';

export const CashflowDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<CashflowMetrics | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      const data = await cashflowApi.getMetrics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to load cashflow metrics:', err);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncSuccess(null);
    setSyncError(null);
    try {
      const data = await cashflowApi.sync();
      setMetrics(data);
      const timeStr = new Date().toLocaleTimeString();
      const sourceLabel =
        data.sync_source === 'LIVE_PAYPAL_SANDBOX'
          ? 'Live PayPal Sandbox Reporting API'
          : 'Sandbox Simulation Ledger';
      setSyncSuccess(`Balances & dispute velocity successfully updated at ${timeStr} (${sourceLabel}).`);
    } catch (err: any) {
      console.error('Failed to sync cashflow metrics:', err);
      setSyncError(err?.response?.data?.detail || err.message || 'Synchronization failed.');
    } finally {
      setSyncing(false);
    }
  };

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await cashflowApi.acknowledgeAlert(alertId);
      await fetchMetrics();
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  const disputeRate = metrics ? Number(metrics.dispute_rate_pct) : 0;
  const isHealthy = disputeRate < 0.65;
  const isWarning = disputeRate >= 0.65 && disputeRate < 1.0;

  return (
    <div className="space-y-6">
      {/* Top Header & Sync Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 sm:p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base sm:text-lg font-bold text-slate-900">
              Cashflow Sentinel & Reserve Forecasting
            </h2>
            {metrics?.sync_source === 'LIVE_PAYPAL_SANDBOX' ? (
              <span className="flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle2 className="w-3 h-3" /> Live Sandbox API
              </span>
            ) : (
              <span className="flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                <Zap className="w-3 h-3" /> Sandbox Simulation
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500">
            Real-time balance monitoring, rolling dispute rate velocity guardrails, and reserve hold prevention.
          </p>
        </div>

        <div className="flex flex-col items-start sm:items-end gap-1 shrink-0">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 transition disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin text-slate-300' : ''}`} />
            <span>{syncing ? 'Connecting to PayPal...' : 'Sync Live PayPal Balances'}</span>
          </button>
          {metrics?.last_synced_at && (
            <span className="text-[11px] text-slate-400 font-mono">
              Last synced: {new Date(metrics.last_synced_at).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Sync Status Notifications */}
      {syncSuccess && (
        <div className="rounded-xl bg-emerald-50 p-4 border border-emerald-200 text-xs font-semibold text-emerald-700 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{syncSuccess}</span>
          </div>
          <button
            onClick={() => setSyncSuccess(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-2 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {syncError && (
        <div className="rounded-xl bg-rose-50 p-4 border border-rose-200 text-xs font-semibold text-rose-700 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{syncError}</span>
          </div>
          <button
            onClick={() => setSyncError(null)}
            className="text-rose-700 hover:text-rose-900 font-bold ml-2 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Active Alerts Feed */}
      {metrics && metrics.active_alerts && metrics.active_alerts.length > 0 && (
        <div className="space-y-3">
          {metrics.active_alerts.map((alert) => (
            <div
              key={alert.id}
              className={`flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border gap-3 ${
                alert.severity === 'CRITICAL'
                  ? 'bg-rose-50 border-rose-200 text-rose-800'
                  : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle
                  className={`w-4 h-4 mt-0.5 shrink-0 ${
                    alert.severity === 'CRITICAL' ? 'text-rose-600' : 'text-amber-600'
                  }`}
                />
                <div>
                  <h4 className="text-xs font-bold">{alert.title}</h4>
                  <p className="text-xs mt-0.5 opacity-90">{alert.message}</p>
                </div>
              </div>
              <button
                onClick={() => handleAcknowledgeAlert(alert.id)}
                className="shrink-0 text-xs font-semibold px-3 py-1.5 rounded-lg bg-white border border-current hover:bg-slate-50 transition cursor-pointer self-start sm:self-auto"
              >
                Acknowledge Alert
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 4-Column Primary KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Available Balance */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Available Balance
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <Wallet className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900">
            ${metrics ? Number(metrics.available_balance).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
          </p>
          <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-100">
            PayPal USD Wallet
          </p>
        </div>

        {/* Pending Reserve */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Pending Reserve
            </span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-amber-800">
            ${metrics ? Number(metrics.pending_balance).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
          </p>
          <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-100">
            Withheld against claims
          </p>
        </div>

        {/* Total Dispute Exposure */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Dispute Liability
            </span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-700 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900">
            ${metrics ? Number(metrics.total_dispute_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
          </p>
          <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-100">
            Across {metrics?.active_dispute_count || 0} active claims
          </p>
        </div>

        {/* 30-Day Volume */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              30-Day Volume
            </span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center">
              <ArrowUpRight className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900">
            ${metrics ? Number(metrics.thirty_day_volume).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
          </p>
          <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-100">
            Fulfillment velocity
          </p>
        </div>
      </div>

      {/* Dispute Rate Health Gauge Card */}
      <div className="bg-white p-5 sm:p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-base font-bold text-slate-900">PayPal Dispute Rate Health Gauge</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              PayPal monitors dispute rate: <span className="font-mono text-slate-700">(Disputed Transactions / Total Transactions) * 100</span>.
            </p>
          </div>
          <div
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold self-start sm:self-auto border ${
              isHealthy
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : isWarning
                ? 'bg-amber-50 text-amber-800 border-amber-200'
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}
          >
            {isHealthy ? <ShieldCheck className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            <span>
              {isHealthy ? 'Healthy Standing' : isWarning ? 'Approaching Limit' : 'Program Breach'}
            </span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
            <span className="text-3xl font-extrabold text-slate-900 tracking-tight shrink-0">{disputeRate.toFixed(2)}%</span>
            <span className="text-xs text-slate-500 font-mono whitespace-nowrap self-start sm:self-auto">Standard Program Max: 1.00%</span>
          </div>

          {/* Progress Bar with markers */}
          <div className="relative w-full h-3 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                isHealthy ? 'bg-emerald-600' : isWarning ? 'bg-amber-600' : 'bg-rose-600'
              }`}
              style={{ width: `${Math.min(disputeRate * 50, 100)}%` }}
            />
          </div>

          <div className="grid grid-cols-3 text-[11px] text-slate-500 font-mono pt-0.5">
            <div className="text-left">
              <span className="font-semibold text-slate-700 block sm:inline">0.00%</span>
              <span className="text-[10px] sm:text-[11px] block sm:inline sm:ml-1 text-slate-400">
                <span className="hidden sm:inline">(Safe)</span>
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

        <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
          <p>
            {isHealthy
              ? 'Merchant dispute velocity is within safe limits. No rolling reserve holds or processing limitations are applied.'
              : isWarning
              ? 'Dispute rate is nearing the 1.00% threshold. Automated evidence submission is recommended for all pending claims.'
              : 'Dispute rate has breached 1.00%. High priority action required to avoid 10-20% PayPal rolling reserves.'}
          </p>
        </div>
      </div>

      {/* Historical Liquidity Snapshots Card */}
      <div className="bg-white p-5 sm:p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900">Historical Liquidity Snapshots</h3>
            <p className="text-xs text-slate-500">
              Audit trail of merchant balance, pending holds, and dispute velocity.
            </p>
          </div>
        </div>

        <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[600px]">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="p-3">Snapshot Date</th>
                  <th className="p-3">Available Balance</th>
                  <th className="p-3">Pending Reserve</th>
                  <th className="p-3">Active Claims</th>
                  <th className="p-3">Dispute Rate</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {metrics?.historical_snapshots?.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-slate-400">
                      No historical snapshots recorded yet.
                    </td>
                  </tr>
                ) : (
                  metrics?.historical_snapshots?.map((snap) => (
                    <tr key={snap.id} className="hover:bg-slate-50">
                      <td className="p-3 font-semibold text-slate-900">{snap.snapshot_date}</td>
                      <td className="p-3 font-bold text-slate-900 font-mono">${Number(snap.available_balance).toFixed(2)}</td>
                      <td className="p-3 text-amber-800 font-semibold font-mono">${Number(snap.pending_balance).toFixed(2)}</td>
                      <td className="p-3 text-slate-700">{snap.active_dispute_count}</td>
                      <td className="p-3 font-mono font-bold text-slate-900">{Number(snap.dispute_rate_pct).toFixed(2)}%</td>
                      <td className="p-3">
                        <span
                          className={`px-2.5 py-0.5 rounded text-[11px] font-semibold border ${
                            Number(snap.dispute_rate_pct) < 0.65
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-amber-50 text-amber-800 border-amber-200'
                          }`}
                        >
                          {Number(snap.dispute_rate_pct) < 0.65 ? 'OPTIMAL' : 'ELEVATED'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
