'use client';

import { useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { CloudOff, RefreshCw } from 'lucide-react';
import { useApiToken } from '@/lib/auth-token';
import { useOfflineStore } from '@/lib/offline-queue';
import { useToast } from '@/components/ui/use-toast';

export function OfflineSyncManager() {
  const online = useOfflineStore((s) => s.online);
  const pendingCount = useOfflineStore((s) => s.pendingCount);
  const syncing = useOfflineStore((s) => s.syncing);
  const setOnline = useOfflineStore((s) => s.setOnline);
  const refresh = useOfflineStore((s) => s.refresh);
  const flush = useOfflineStore((s) => s.flush);

  const getToken = useApiToken();
  const qc = useQueryClient();
  const { toast } = useToast();

  const runFlush = useCallback(async () => {
    const synced = await flush(getToken);
    if (synced > 0) {
      qc.invalidateQueries({ queryKey: ['history'] });
      toast({
        title: `Synced ${synced} screening${synced > 1 ? 's' : ''}`,
        description: 'Saved from your offline queue.',
      });
    }
  }, [flush, getToken, qc, toast]);

  useEffect(() => {
    setOnline(typeof navigator === 'undefined' ? true : navigator.onLine);
    void refresh();
    if (typeof navigator !== 'undefined' && navigator.onLine) void runFlush();

    const onOnline = () => {
      setOnline(true);
      void runFlush();
    };
    const onOffline = () => setOnline(false);

    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, [refresh, runFlush, setOnline]);

  if (online && pendingCount === 0 && !syncing) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 left-4 z-50 flex items-center gap-2 rounded-full border bg-background/95 px-3 py-2 text-xs font-medium shadow-lg backdrop-blur"
    >
      {syncing ? (
        <>
          <RefreshCw className="h-3.5 w-3.5 animate-spin text-sky-600" />
          Syncing…
        </>
      ) : !online ? (
        <>
          <CloudOff className="h-3.5 w-3.5 text-amber-600" />
          Offline{pendingCount > 0 ? ` · ${pendingCount} queued` : ''}
        </>
      ) : (
        <>
          <RefreshCw className="h-3.5 w-3.5 text-sky-600" />
          {pendingCount} screening{pendingCount > 1 ? 's' : ''} pending sync
        </>
      )}
    </div>
  );
}
