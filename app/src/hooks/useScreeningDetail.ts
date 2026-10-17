'use client';

import { useQuery } from '@tanstack/react-query';
import { getHistoryDetail, getScreening } from '@/lib/api';
import { useApiToken } from '@/lib/auth-token';
import { getLocalScreening } from '@/lib/local-store';
import type { ScreeningResult } from '@/lib/types';

export function useScreeningDetail(id: string | undefined) {
  const getToken = useApiToken();

  return useQuery<ScreeningResult | null>({
    queryKey: ['screening', id],
    enabled: Boolean(id),
    queryFn: async () => {
      if (!id) return null;

      const local = await getLocalScreening(id);
      if (local) return local;

      try {
        const token = await getToken();
        try {
          return await getHistoryDetail(id, token);
        } catch {
          return await getScreening(id, token);
        }
      } catch {
        return null;
      }
    },
  });
}
