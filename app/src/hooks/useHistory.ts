'use client';

import { useQuery } from '@tanstack/react-query';
import { getHistory } from '@/lib/api';
import { useApiToken } from '@/lib/auth-token';
import { listLocalScreenings, listPending } from '@/lib/local-store';
import type { HistoryItem, HistoryResponse } from '@/lib/types';

async function fetchHistory(
  getToken: () => Promise<string | null>,
  params: { limit?: number; offset?: number; risk_category?: string }
): Promise<HistoryResponse> {
  const limit = params.limit ?? 20;
  const offset = params.offset ?? 0;

  let remote: HistoryItem[] = [];
  let total = 0;
  try {
    const token = await getToken();
    const res = await getHistory(token, params);
    remote = res.screenings;
    total = res.total;
  } catch {
    // API/DB unavailable — fall back to locally stored screenings.
  }

  const local = await listLocalScreenings();
  const pending = await listPending();
  const pendingItems: HistoryItem[] = pending.map((p) => ({
    id: p.local_id,
    created_at: p.created_at,
    health_score: 0,
    risk_category: 'pending',
    pending: true,
  }));

  const seen = new Set(remote.map((s) => s.id));
  const merged = [
    ...pendingItems,
    ...remote,
    ...local.filter((s) => !seen.has(s.id)),
  ].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return {
    screenings: merged.slice(offset, offset + limit),
    total: Math.max(total, merged.length),
    limit,
    offset,
  };
}

export function useHistory(params: { limit?: number; offset?: number; risk_category?: string } = {}) {
  const getToken = useApiToken();
  return useQuery({
    queryKey: ['history', params],
    queryFn: () => fetchHistory(getToken, params),
  });
}
