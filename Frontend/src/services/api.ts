import { SystemStatus, PrivacySettings, ProcessedDocument, FinancialInsight, DeviceTelemetry } from '../types/momo';

const API_BASE = '/api';

export async function fetchHealth(): Promise<{ status: string; service: string }> {
  const res = await fetch(`${API_BASE}/health/`);
  if (!res.ok) throw new Error(`Health check failed (${res.status})`);
  return res.json();
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/system/status/`);
  if (!res.ok) throw new Error(`System status failed (${res.status})`);
  return res.json();
}

export async function fetchOllamaStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/ollama/status/`);
  if (!res.ok) throw new Error(`Ollama status failed (${res.status})`);
  return res.json();
}

export async function fetchOllamaModels(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/ollama/models/`);
  if (!res.ok) throw new Error(`Ollama models failed (${res.status})`);
  const data = await res.json();
  return data.model_names || [];
}

export async function fetchDevices(): Promise<DeviceTelemetry[]> {
  const res = await fetch(`${API_BASE}/devices/`);
  if (!res.ok) throw new Error(`Fetch devices failed (${res.status})`);
  const data = await res.json();
  return Object.values(data.devices || {});
}

export async function fetchDocuments(): Promise<ProcessedDocument[]> {
  const res = await fetch(`${API_BASE}/documents/`);
  if (!res.ok) throw new Error(`Fetch documents failed (${res.status})`);
  const data = await res.json();
  return data.documents || [];
}

export async function uploadDocument(file: File): Promise<{ document: ProcessedDocument; financial_insight?: FinancialInsight }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/documents/`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Document upload failed (${res.status})`);
  return res.json();
}

export async function uploadRawText(text: string, filename: string = 'pasted_invoice.txt'): Promise<{ document: ProcessedDocument; financial_insight?: FinancialInsight }> {
  const res = await fetch(`${API_BASE}/documents/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, filename }),
  });
  if (!res.ok) throw new Error(`Text upload failed (${res.status})`);
  return res.json();
}

export async function fetchDocumentDetail(id: string): Promise<{ document: ProcessedDocument; financial_insight?: FinancialInsight }> {
  const res = await fetch(`${API_BASE}/documents/${id}/`);
  if (!res.ok) throw new Error(`Fetch document detail failed (${res.status})`);
  return res.json();
}

export async function fetchFinanceDetail(documentId: string): Promise<FinancialInsight> {
  const res = await fetch(`${API_BASE}/finance/${documentId}/`);
  if (!res.ok) throw new Error(`Fetch finance detail failed (${res.status})`);
  return res.json();
}

export async function fetchPrivacySettings(): Promise<PrivacySettings> {
  const res = await fetch(`${API_BASE}/settings/privacy/`);
  if (!res.ok) throw new Error(`Fetch privacy failed (${res.status})`);
  const data = await res.json();
  return data.settings;
}

export async function updatePrivacySettings(updates: Partial<PrivacySettings>): Promise<PrivacySettings> {
  const res = await fetch(`${API_BASE}/settings/privacy/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Update privacy failed (${res.status})`);
  const data = await res.json();
  return data.settings;
}

export async function fetchMemories(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/memory/`);
  if (!res.ok) throw new Error(`Fetch memories failed (${res.status})`);
  const data = await res.json();
  return data.memories || [];
}

export async function wipeMemories(): Promise<void> {
  const res = await fetch(`${API_BASE}/memory/`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Wipe memory failed (${res.status})`);
}
