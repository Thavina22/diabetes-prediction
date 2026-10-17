'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createApiKey, listApiKeys, revokeApiKey, toApiError } from '@/lib/api';
import { useApiToken } from '@/lib/auth-token';
import { toast } from '@/components/ui/use-toast';

export function useApiKeys() {
  const getToken = useApiToken();
  return useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => listApiKeys(await getToken()),
    retry: false,
  });
}

export function useCreateApiKey() {
  const getToken = useApiToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; scopes: string[]; rate_limit_rpm: number }) =>
      createApiKey(body, await getToken()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (err) => {
      const { detail, status } = toApiError(err);
      toast({
        variant: 'destructive',
        title: status === 503 ? 'Persistence not configured' : 'Could not create key',
        description: status === 503 ? 'Connect a database to store API keys.' : detail,
      });
    },
  });
}

export function useRevokeApiKey() {
  const getToken = useApiToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => revokeApiKey(id, await getToken()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['api-keys'] });
      toast({ title: 'API key revoked' });
    },
  });
}
