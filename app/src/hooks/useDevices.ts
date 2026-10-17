'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  connectDevice,
  disconnectDevice,
  listDevices,
  syncDevice,
  toApiError,
} from '@/lib/api';
import { useApiToken } from '@/lib/auth-token';
import type { DeviceConnectionCreate } from '@/lib/types';
import { toast } from '@/components/ui/use-toast';

export function useDevices() {
  const getToken = useApiToken();
  return useQuery({
    queryKey: ['devices'],
    queryFn: async () => {
      const token = await getToken();
      return listDevices(token);
    },
    retry: false,
  });
}

export function useConnectDevice() {
  const getToken = useApiToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: DeviceConnectionCreate) => {
      const token = await getToken();
      return connectDevice(body, token);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices'] });
      toast({ title: 'Device connected' });
    },
    onError: (err) => {
      const { detail, status } = toApiError(err);
      toast({
        variant: 'destructive',
        title: status === 503 ? 'Persistence not configured' : 'Could not connect device',
        description:
          status === 503
            ? 'Connect a database to store device connections.'
            : detail,
      });
    },
  });
}

export function useDisconnectDevice() {
  const getToken = useApiToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      await disconnectDevice(id, token);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices'] });
      toast({ title: 'Device disconnected' });
    },
  });
}

export function useSyncDevice() {
  const getToken = useApiToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return syncDevice(id, token);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['devices'] });
      toast({
        title: 'Sync complete',
        description: `${res.synced_records} record${res.synced_records === 1 ? '' : 's'} pulled.`,
      });
    },
    onError: (err) => {
      const { detail } = toApiError(err);
      toast({ variant: 'destructive', title: 'Sync failed', description: detail });
    },
  });
}
