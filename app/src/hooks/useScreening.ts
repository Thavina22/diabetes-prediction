'use client';

import { useCallback, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createScreening, isNetworkError, toApiError } from '@/lib/api';
import { useApiToken } from '@/lib/auth-token';
import { enqueuePending, saveLocalScreening } from '@/lib/local-store';
import { useOfflineStore } from '@/lib/offline-queue';
import type { ScreeningInput, ScreeningResult } from '@/lib/types';
import { toast } from '@/components/ui/use-toast';

export function useCreateScreening() {
  const getToken = useApiToken();
  const qc = useQueryClient();

  return useMutation<ScreeningResult, unknown, ScreeningInput>({
    mutationFn: async (input) => {
      const token = await getToken();
      const result = await createScreening(input, token);
      await saveLocalScreening(result);
      return result;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['history'] });
    },
    onError: (err) => {
      // Network failures are handled by the offline queue — stay quiet here.
      if (isNetworkError(err)) return;
      const { detail } = toApiError(err);
      toast({
        variant: 'destructive',
        title: 'Screening failed',
        description: detail,
      });
    },
  });
}

/**
 * Submit a screening, transparently falling back to the offline queue when the
 * device is offline or the API is unreachable.
 */
export function useSubmitScreening() {
  const mutation = useCreateScreening();
  const refresh = useOfflineStore((s) => s.refresh);
  const [queued, setQueued] = useState(false);

  const submit = useCallback(
    async (payload: ScreeningInput): Promise<ScreeningResult | null> => {
      const offline = typeof navigator !== 'undefined' && !navigator.onLine;
      if (offline) {
        await enqueuePending(payload);
        await refresh();
        setQueued(true);
        return null;
      }
      try {
        return await mutation.mutateAsync(payload);
      } catch (err) {
        if (isNetworkError(err)) {
          await enqueuePending(payload);
          await refresh();
          setQueued(true);
          return null;
        }
        throw err;
      }
    },
    [mutation, refresh]
  );

  return {
    submit,
    isPending: mutation.isPending,
    queued,
    reset: () => setQueued(false),
  };
}
