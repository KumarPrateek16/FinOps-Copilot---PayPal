import axios from 'axios';
import {
  Dispute,
  HITLQueueItem,
  HITLDecisionPayload,
  Invoice,
  ExtractedInvoiceData,
  CashflowMetrics,
  FinancialAlert,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const disputesApi = {
  list: async (statusFilter?: string): Promise<Dispute[]> => {
    const params = statusFilter ? { status: statusFilter } : {};
    const res = await apiClient.get<Dispute[]>('/disputes', { params });
    return res.data;
  },

  get: async (disputeId: string): Promise<Dispute> => {
    const res = await apiClient.get<Dispute>(`/disputes/${disputeId}`);
    return res.data;
  },

  getHITLQueue: async (): Promise<HITLQueueItem[]> => {
    const res = await apiClient.get<HITLQueueItem[]>('/disputes/hitl/queue');
    return res.data;
  },

  submitHITLAction: async (disputeId: string, payload: HITLDecisionPayload): Promise<Dispute> => {
    const res = await apiClient.post<Dispute>(`/disputes/${disputeId}/hitl/action`, payload);
    return res.data;
  },
};

export const invoicesApi = {
  extract: async (file: File): Promise<ExtractedInvoiceData> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<ExtractedInvoiceData>('/invoices/extract', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  create: async (data: {
    invoice_number: string;
    recipient_name: string;
    recipient_email: string;
    currency: string;
    payment_terms: string;
    line_items: any[];
  }): Promise<Invoice> => {
    const res = await apiClient.post<Invoice>('/invoices', data);
    return res.data;
  },

  list: async (statusFilter?: string): Promise<Invoice[]> => {
    const params = statusFilter ? { status: statusFilter } : {};
    const res = await apiClient.get<Invoice[]>('/invoices', { params });
    return res.data;
  },

  get: async (invoiceId: string): Promise<Invoice> => {
    const res = await apiClient.get<Invoice>(`/invoices/${invoiceId}`);
    return res.data;
  },

  send: async (invoiceId: string): Promise<Invoice> => {
    const res = await apiClient.post<Invoice>(`/invoices/${invoiceId}/send`);
    return res.data;
  },
};

export const cashflowApi = {
  getMetrics: async (): Promise<CashflowMetrics> => {
    const res = await apiClient.get<CashflowMetrics>('/cashflow/metrics');
    return res.data;
  },

  sync: async (): Promise<CashflowMetrics> => {
    const res = await apiClient.post<CashflowMetrics>('/cashflow/sync');
    return res.data;
  },

  getAlerts: async (includeAcknowledged: boolean = false): Promise<FinancialAlert[]> => {
    const res = await apiClient.get<FinancialAlert[]>('/cashflow/alerts', {
      params: { include_acknowledged: includeAcknowledged },
    });
    return res.data;
  },

  acknowledgeAlert: async (alertId: string): Promise<FinancialAlert> => {
    const res = await apiClient.post<FinancialAlert>(`/cashflow/alerts/${alertId}/acknowledge`);
    return res.data;
  },
};

export interface ConnectPayload {
  client_id?: string;
  client_secret?: string;
  environment?: 'sandbox' | 'production';
  merchant_name?: string;
}

export interface ConnectResult {
  success: boolean;
  merchant_name: string;
  environment: string;
  app_id: string | null;
  client_id_masked: string;
  scopes: string[];
  expires_in: number;
  token_type: string;
  connected_at: string;
  message: string;
}

export const authApi = {
  connect: async (payload: ConnectPayload): Promise<ConnectResult> => {
    const res = await apiClient.post<ConnectResult>('/auth/connect', payload);
    return res.data;
  },

  getStatus: async (): Promise<{
    environment: string;
    base_url: string;
    configured: boolean;
    client_id_masked: string | null;
  }> => {
    const res = await apiClient.get('/auth/status');
    return res.data;
  },
};


