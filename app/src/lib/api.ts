import axios, { AxiosError } from 'axios';
import type {
  ScreeningInput,
  ScreeningResult,
  HistoryResponse,
  MLResult,
  DeviceConnection,
  DeviceConnectionCreate,
} from '@/lib/types';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

export interface ApiErrorShape {
  status: number;
  detail: string;
}

export function toApiError(err: unknown): ApiErrorShape {
  if (axios.isAxiosError(err)) {
    const ax = err as AxiosError<{ detail?: string }>;
    const detail =
      ax.response?.data?.detail ??
      (ax.code === 'ERR_NETWORK'
        ? 'Cannot reach the API. Is the backend running?'
        : ax.message);
    return { status: ax.response?.status ?? 0, detail };
  }
  return { status: 0, detail: err instanceof Error ? err.message : 'Unknown error' };
}

export function isNetworkError(err: unknown): boolean {
  if (axios.isAxiosError(err)) {
    return !err.response || err.code === 'ERR_NETWORK' || err.code === 'ECONNABORTED';
  }
  return false;
}

async function authHeaders(token: string | null) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function createScreening(
  input: ScreeningInput,
  token: string | null
): Promise<ScreeningResult> {
  const res = await api.post<ScreeningResult>(
    '/api/v1/screening',
    input,
    { headers: await authHeaders(token) }
  );
  return res.data;
}

export async function getScreening(
  id: string,
  token: string | null
): Promise<ScreeningResult> {
  const res = await api.get<ScreeningResult>(`/api/v1/screening/${id}`, {
    headers: await authHeaders(token),
  });
  return res.data;
}

export async function getHistory(
  token: string | null,
  params: { limit?: number; offset?: number; risk_category?: string } = {}
): Promise<HistoryResponse> {
  const res = await api.get<HistoryResponse>('/api/v1/history', {
    params,
    headers: await authHeaders(token),
  });
  return res.data;
}

export async function getHistoryDetail(
  id: string,
  token: string | null
): Promise<ScreeningResult> {
  const res = await api.get<ScreeningResult>(`/api/v1/history/${id}`, {
    headers: await authHeaders(token),
  });
  return res.data;
}

export async function predictMl(
  input: ScreeningInput,
  token: string | null
): Promise<MLResult> {
  const res = await api.post<MLResult>('/api/v1/ml/predict', input, {
    headers: await authHeaders(token),
  });
  return res.data;
}

export async function listDevices(token: string | null): Promise<DeviceConnection[]> {
  const res = await api.get<DeviceConnection[]>('/api/v1/devices', {
    headers: await authHeaders(token),
  });
  return res.data;
}

export async function connectDevice(
  body: DeviceConnectionCreate,
  token: string | null
): Promise<DeviceConnection> {
  const res = await api.post<DeviceConnection>('/api/v1/devices', body, {
    headers: await authHeaders(token),
  });
  return res.data;
}

export async function disconnectDevice(id: string, token: string | null): Promise<void> {
  await api.delete(`/api/v1/devices/${id}`, { headers: await authHeaders(token) });
}

export async function syncDevice(
  id: string,
  token: string | null
): Promise<{ status: string; synced_records: number }> {
  const res = await api.post(`/api/v1/devices/${id}/sync`, null, {
    headers: await authHeaders(token),
  });
  return res.data;
}

export function exportUrl(id: string, format: 'pdf' | 'fhir' | 'cda') {
  return `${API_BASE_URL}/api/v1/history/${id}/export?format=${format}`;
}

export async function downloadExport(
  id: string,
  format: 'pdf' | 'fhir' | 'cda',
  token: string | null
): Promise<Blob> {
  const res = await api.get(`/api/v1/history/${id}/export`, {
    params: { format },
    responseType: 'blob',
    headers: await authHeaders(token),
  });
  return res.data as Blob;
}
