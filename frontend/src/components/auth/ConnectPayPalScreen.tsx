import React, { useState } from 'react';
import {
  ArrowRight,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { authApi } from '../../services/api';

export interface MerchantSession {
  merchantName: string;
  clientId: string;
  appId?: string;
  environment: 'sandbox' | 'production';
  connectedAt: string;
  scopes?: string[];
}

interface ConnectPayPalScreenProps {
  onConnect: (session: MerchantSession) => void;
}

export const ConnectPayPalScreen: React.FC<ConnectPayPalScreenProps> = ({ onConnect }) => {
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customName, setCustomName] = useState('Acme Electronics');
  const [customClientId, setCustomClientId] = useState('');
  const [customSecret, setCustomSecret] = useState('');
  const [environment, setEnvironment] = useState<'sandbox' | 'production'>('sandbox');

  const [loading, setLoading] = useState(false);
  const [connectionStep, setConnectionStep] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Authenticate live against PayPal Sandbox using backend-configured developer credentials
  const handleConnectDefault = async () => {
    setLoading(true);
    setErrorMessage(null);
    setConnectionStep('Connecting to PayPal Sandbox...');

    try {
      const result = await authApi.connect({
        environment: 'sandbox',
        merchant_name: 'Acme Electronics',
      });

      setConnectionStep('Verifying OAuth2 token & permissions...');

      setTimeout(() => {
        onConnect({
          merchantName: result.merchant_name || 'Acme Electronics',
          clientId: result.client_id_masked || 'Ac_TnomDI...SHtBq',
          appId: result.app_id || undefined,
          environment: 'sandbox',
          connectedAt: result.connected_at || new Date().toISOString(),
          scopes: result.scopes,
        });
      }, 500);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Failed to connect to PayPal. Please ensure the backend is running.';
      setErrorMessage(msg);
      setConnectionStep('');
      setLoading(false);
    }
  };

  // Authenticate custom developer credentials provided by the merchant
  const handleCustomConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customClientId.trim() || !customSecret.trim()) {
      setErrorMessage('Please enter both your Client ID and Client Secret.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    setConnectionStep('Verifying credentials with PayPal...');

    try {
      const result = await authApi.connect({
        client_id: customClientId.trim(),
        client_secret: customSecret.trim(),
        environment,
        merchant_name: customName.trim() || 'Custom Merchant',
      });

      setConnectionStep('Authentication successful. Redirecting...');

      setTimeout(() => {
        onConnect({
          merchantName: result.merchant_name || customName || 'Custom Merchant',
          clientId: result.client_id_masked || customClientId.slice(0, 8) + '...',
          appId: result.app_id || undefined,
          environment,
          connectedAt: result.connected_at || new Date().toISOString(),
          scopes: result.scopes,
        });
      }, 500);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'PayPal Authentication Failed: Invalid credentials.';
      setErrorMessage(msg);
      setConnectionStep('');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/60 flex flex-col items-center justify-center p-4 sm:p-6 font-sans text-slate-900 antialiased selection:bg-slate-900 selection:text-white">
      <div className="w-full max-w-sm sm:max-w-md space-y-6">
        {/* Main Minimalist Connect Card */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-7 sm:p-9 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-6">
          {/* Header */}
          <div className="space-y-2.5 text-center">
            <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl bg-slate-900 text-white font-bold text-sm shadow-sm">
              <span>FP</span>
            </div>
            <div className="space-y-1">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                FinOps Copilot
              </h1>
              <p className="text-xs text-slate-500">
                Autonomous Dispute Defense & Invoicing V2 for PayPal
              </p>
            </div>
          </div>

          {/* Error Notice */}
          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="font-semibold">Authentication Error</p>
                <p className="text-[11px] text-rose-700 leading-relaxed">{errorMessage}</p>
              </div>
            </div>
          )}

          {!showCustomForm ? (
            <div className="space-y-4 pt-1">
              {/* Single Primary Action: Connect PayPal Sandbox */}
              <button
                onClick={handleConnectDefault}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white font-medium text-xs transition shadow-sm cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>{connectionStep || 'Connecting...'}</span>
                  </>
                ) : (
                  <>
                    <span>Connect PayPal Sandbox</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>

              {/* Minimalist toggle for custom developer credentials */}
              <div className="text-center pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    setShowCustomForm(true);
                  }}
                  className="text-xs text-slate-400 hover:text-slate-800 transition cursor-pointer"
                >
                  Use custom developer credentials
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleCustomConnect} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Merchant Name
                </label>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="e.g. Acme Electronics"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-slate-800 focus:outline-none transition"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  PayPal Client ID
                </label>
                <input
                  type="text"
                  value={customClientId}
                  onChange={(e) => setCustomClientId(e.target.value)}
                  placeholder="From developer.paypal.com"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-slate-800 focus:outline-none transition"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  PayPal Client Secret
                </label>
                <input
                  type="password"
                  value={customSecret}
                  onChange={(e) => setCustomSecret(e.target.value)}
                  placeholder="Client Secret"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-slate-800 focus:outline-none transition"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Environment
                </label>
                <select
                  value={environment}
                  onChange={(e) => setEnvironment(e.target.value as 'sandbox' | 'production')}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-slate-800 focus:outline-none transition"
                >
                  <option value="sandbox">Sandbox (api-m.sandbox.paypal.com)</option>
                  <option value="production">Production (api-m.paypal.com)</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    setShowCustomForm(false);
                  }}
                  className="text-xs text-slate-500 hover:text-slate-800 transition cursor-pointer"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-lg bg-slate-900 text-white px-4 py-2 text-xs font-semibold hover:bg-slate-800 active:bg-slate-950 transition cursor-pointer disabled:opacity-50"
                >
                  {loading ? 'Verifying...' : 'Verify & Connect'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
