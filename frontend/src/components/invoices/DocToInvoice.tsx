import React, { useState, useEffect } from 'react';
import {
  Upload,
  Sparkles,
  Send,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  FileText,
} from 'lucide-react';
import { Invoice, InvoiceLineItem, ExtractedInvoiceData } from '../../types';
import { invoicesApi } from '../../services/api';

export const DocToInvoice: React.FC = () => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Form State - initialized empty with placeholders until PO is extracted or merchant adds items
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [recipientName, setRecipientName] = useState('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [paymentTerms, setPaymentTerms] = useState('DUE_ON_RECEIPT');
  const [confidenceScore, setConfidenceScore] = useState<number | null>(null);
  const [lineItems, setLineItems] = useState<InvoiceLineItem[]>([]);

  const loadInvoices = async () => {
    setLoadingList(true);
    try {
      const data = await invoicesApi.list();
      setInvoices(data);
    } catch (err) {
      console.error('Failed to load invoices:', err);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadInvoices();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleExtract = async () => {
    if (!selectedFile) return;
    setExtracting(true);
    setErrorBanner(null);
    setSuccessBanner(null);

    try {
      const extracted: ExtractedInvoiceData = await invoicesApi.extract(selectedFile);
      setInvoiceNumber(extracted.invoice_number);
      setRecipientName(extracted.recipient_name);
      setRecipientEmail(extracted.recipient_email);
      setCurrency(extracted.currency);
      setPaymentTerms(extracted.payment_terms || 'DUE_ON_RECEIPT');
      setConfidenceScore(Number(extracted.confidence_score));
      if (extracted.line_items && extracted.line_items.length > 0) {
        setLineItems(
          extracted.line_items.map((item) => ({
            item_name: item.item_name,
            description: item.description,
            quantity: Number(item.quantity),
            unit_price: Number(item.unit_price),
            tax_rate: Number(item.tax_rate || 0),
            total: Number(item.total),
          }))
        );
      }
      setSuccessBanner(`Successfully extracted fields from ${selectedFile.name} with Gemini 2.5 Flash!`);
    } catch (err: any) {
      setErrorBanner(err?.response?.data?.detail || err.message || 'Extraction failed.');
    } finally {
      setExtracting(false);
    }
  };

  const handleLineItemChange = (index: number, field: keyof InvoiceLineItem, value: any) => {
    const updated = [...lineItems];
    const item = { ...updated[index], [field]: value };
    if (field === 'quantity' || field === 'unit_price') {
      item.total = Number(item.quantity) * Number(item.unit_price);
    }
    updated[index] = item;
    setLineItems(updated);
  };

  const addLineItem = () => {
    setLineItems([
      ...lineItems,
      {
        item_name: '',
        description: '',
        quantity: 1,
        unit_price: 0,
        tax_rate: 0,
        total: 0,
      },
    ]);
  };

  const removeLineItem = (index: number) => {
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const grandTotal = lineItems.reduce((acc, item) => acc + Number(item.total || 0), 0);

  const handleCreateAndSend = async () => {
    if (!invoiceNumber || !recipientEmail || lineItems.length === 0 || grandTotal <= 0) {
      setErrorBanner('Please extract a document or enter an invoice number, recipient email, and at least one line item.');
      return;
    }

    setSending(true);
    setErrorBanner(null);
    setSuccessBanner(null);

    try {
      // 1. Create draft invoice
      const created = await invoicesApi.create({
        invoice_number: invoiceNumber,
        recipient_name: recipientName,
        recipient_email: recipientEmail,
        currency,
        payment_terms: paymentTerms,
        line_items: lineItems,
      });

      // 2. Dispatch via PayPal Invoicing V2
      const sent = await invoicesApi.send(created.id);
      setSuccessBanner(
        `Invoice #${sent.invoice_number} successfully dispatched to ${sent.recipient_email} via PayPal Invoicing V2! (PayPal ID: ${sent.paypal_invoice_id})`
      );
      await loadInvoices();
    } catch (err: any) {
      setErrorBanner(err?.response?.data?.detail || err.message || 'Invoice creation or dispatch failed.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Notifications */}
      {successBanner && (
        <div className="rounded-xl bg-emerald-50 p-4 border border-emerald-200 text-xs font-semibold text-emerald-700 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>{successBanner}</span>
          </div>
          <button
            onClick={() => setSuccessBanner(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-2 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}
      {errorBanner && (
        <div className="rounded-xl bg-rose-50 p-4 border border-rose-200 text-xs font-semibold text-rose-700 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-rose-700 hover:text-rose-900 font-bold ml-2 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid: Upload Dropzone + Invoice Builder */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: PO Ingestion Card */}
        <div className="bg-white p-5 sm:p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm pb-3 border-b border-slate-100">
            <div className="w-7 h-7 rounded-md bg-slate-900 text-white flex items-center justify-center">
              <Upload className="w-3.5 h-3.5" />
            </div>
            <span>Multimodal PO Ingestion</span>
          </div>

          <p className="text-xs text-slate-500 leading-relaxed">
            Upload purchase orders, contracts, or estimates. Gemini 2.5 Vision parses line items, amounts, and buyer details directly into PayPal schemas.
          </p>

          {/* Drag & Drop File Zone */}
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center hover:border-slate-800 transition cursor-pointer relative bg-slate-50">
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              onChange={handleFileChange}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
            <FileText className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-800">
              {selectedFile ? selectedFile.name : 'Choose PO file or drop it here'}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">PDF, PNG, JPG up to 10MB</p>
          </div>

          <button
            onClick={handleExtract}
            disabled={!selectedFile || extracting}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-slate-900 py-2.5 px-4 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 transition disabled:opacity-50 cursor-pointer"
          >
            <Sparkles className={`w-3.5 h-3.5 ${extracting ? 'animate-spin' : ''}`} />
            <span>{extracting ? 'Extracting with Gemini...' : 'Extract Invoice Fields'}</span>
          </button>

          {confidenceScore !== null && (
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
              <span className="text-slate-600 font-medium">Gemini Confidence:</span>
              <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {Math.round(confidenceScore * 100)}%
              </span>
            </div>
          )}
        </div>

        {/* Right Column: Structured Invoice Editor */}
        <div className="lg:col-span-2 bg-white p-5 sm:p-6 rounded-xl border border-slate-200 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div>
              <h3 className="text-base font-bold text-slate-900">Structured Invoice Builder</h3>
              <p className="text-xs text-slate-500">
                Review and modify extracted fields before dispatching via PayPal Invoicing V2.
              </p>
            </div>
            <div className="text-left sm:text-right">
              <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold block">
                Total Invoice Amount
              </span>
              <p className="text-2xl font-extrabold text-slate-900">
                ${grandTotal.toFixed(2)}{' '}
                <span className="text-xs font-normal text-slate-500">{currency}</span>
              </p>
            </div>
          </div>

          {/* Form Fields Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Invoice Number
              </label>
              <input
                type="text"
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                placeholder="e.g. INV-2026-001 (auto-populated upon extraction)"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 placeholder:text-slate-400 focus:border-slate-800 focus:outline-none transition"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Payment Terms
              </label>
              <select
                value={paymentTerms}
                onChange={(e) => setPaymentTerms(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-slate-800 focus:outline-none transition"
              >
                <option value="DUE_ON_RECEIPT">Due on Receipt</option>
                <option value="NET_10">Net 10 Days</option>
                <option value="NET_30">Net 30 Days</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Recipient Company / Name
              </label>
              <input
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                placeholder="e.g. Acme Corporation (auto-populated upon extraction)"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-800 focus:outline-none transition"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Recipient PayPal Email
              </label>
              <input
                type="email"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                placeholder="e.g. billing@company.com (auto-populated upon extraction)"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-800 focus:outline-none transition"
              />
            </div>
          </div>

          {/* Line Items Editor with Responsive Overflow Wrapper */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900">Line Items</span>
              <button
                onClick={addLineItem}
                className="flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-900 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Item</span>
              </button>
            </div>

            <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs min-w-[500px]">
                  <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                    <tr>
                      <th className="p-3">Item Description</th>
                      <th className="p-3 w-20 text-center">Qty</th>
                      <th className="p-3 w-28 text-right">Unit Price</th>
                      <th className="p-3 w-28 text-right">Total</th>
                      <th className="p-3 w-10"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {lineItems.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-8 px-4 text-center text-slate-400 bg-slate-50/50">
                          <div className="max-w-sm mx-auto space-y-1">
                            <p className="font-semibold text-slate-600 text-xs">No line items yet</p>
                            <p className="text-[11px] text-slate-400">
                              Drop a purchase order, contract, or estimate on the left to auto-extract line items, or click <strong>+ Add Item</strong> to enter manually.
                            </p>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      lineItems.map((item, index) => (
                        <tr key={index} className="hover:bg-slate-50">
                          <td className="p-2.5">
                            <input
                              type="text"
                              value={item.item_name}
                              onChange={(e) => handleLineItemChange(index, 'item_name', e.target.value)}
                              placeholder="e.g. Enterprise Cloud Platform License"
                              className="w-full font-medium text-slate-900 placeholder:text-slate-400 border-0 bg-transparent p-1 focus:ring-1 focus:ring-slate-800 rounded text-xs"
                            />
                          </td>
                          <td className="p-2.5">
                            <input
                              type="number"
                              value={item.quantity || ''}
                              onChange={(e) => handleLineItemChange(index, 'quantity', Number(e.target.value))}
                              placeholder="1"
                              className="w-full text-slate-900 placeholder:text-slate-400 border-0 bg-transparent p-1 focus:ring-1 focus:ring-slate-800 rounded text-center text-xs"
                            />
                          </td>
                          <td className="p-2.5">
                            <input
                              type="number"
                              value={item.unit_price || ''}
                              onChange={(e) => handleLineItemChange(index, 'unit_price', Number(e.target.value))}
                              placeholder="0.00"
                              className="w-full text-slate-900 placeholder:text-slate-400 border-0 bg-transparent p-1 focus:ring-1 focus:ring-slate-800 rounded text-right font-mono text-xs"
                            />
                          </td>
                          <td className="p-2.5 text-right font-bold text-slate-900 font-mono text-xs">
                            ${Number(item.total || 0).toFixed(2)}
                          </td>
                          <td className="p-2.5 text-center">
                            <button
                              onClick={() => removeLineItem(index)}
                              className="text-slate-400 hover:text-rose-600 transition cursor-pointer p-1"
                              aria-label="Remove line item"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Action Row */}
          <div className="pt-2 flex justify-end">
            <button
              onClick={handleCreateAndSend}
              disabled={sending || grandTotal <= 0 || !recipientEmail || !invoiceNumber}
              className="flex items-center gap-2 rounded-lg bg-slate-900 py-2.5 px-5 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{sending ? 'Dispatching to PayPal...' : 'Save & Dispatch via PayPal Invoicing V2'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Dispatched Invoices History Card */}
      <div className="bg-white p-5 sm:p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-900">Dispatched Invoices History</h3>
            <p className="text-xs text-slate-500">
              Synchronized merchant ledger across PayPal Invoicing V2.
            </p>
          </div>
          <button
            onClick={loadInvoices}
            disabled={loadingList}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 transition cursor-pointer self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingList ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[600px]">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="p-3">Invoice #</th>
                  <th className="p-3">PayPal Invoice ID</th>
                  <th className="p-3">Customer</th>
                  <th className="p-3">Amount</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-slate-400">
                      No invoices created yet. Extract a purchase order above to create your first invoice!
                    </td>
                  </tr>
                ) : (
                  invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50">
                      <td className="p-3 font-mono font-bold text-slate-900">{inv.invoice_number}</td>
                      <td className="p-3 font-mono text-slate-500">{inv.paypal_invoice_id || 'LOCAL_DRAFT'}</td>
                      <td className="p-3 font-medium text-slate-900">
                        {inv.recipient_name}
                        <span className="block text-[11px] text-slate-400">{inv.recipient_email}</span>
                      </td>
                      <td className="p-3 font-bold text-slate-900 font-mono">
                        ${Number(inv.total_amount).toFixed(2)} {inv.currency}
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2.5 py-0.5 rounded text-[11px] font-semibold border ${
                            inv.status === 'SENT'
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-slate-100 text-slate-700 border-slate-200'
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>
                      <td className="p-3 text-slate-500 font-mono">
                        {new Date(inv.created_at).toLocaleDateString()}
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
