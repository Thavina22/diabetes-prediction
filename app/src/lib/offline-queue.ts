'use client';

import { create } from 'zustand';
import { createScreening } from '@/lib/api';
import {
  countPending,
  listPending,
  removePending,
  saveLocalScreening,
} from '@/lib/local-store';

interface OfflineState {
  pendingCount: number;
  online: boolean;
  syncing: boolean;
  lastSyncedAt: number | null;
  setOnline: (value: boolean) => void;
  refresh: () => Promise<void>;
  flush: (getToken: () => Promise<string | null>) => Promise<number>;
}

export const useOfflineStore = create<OfflineState>((set, get) => ({
  pendingCount: 0,
  online: true,
  syncing: false,
  lastSyncedAt: null,
  setOnline: (value) => set({ online: value }),
  refresh: async () => {
    set({ pendingCount: await countPending() });
  },
  flush: async (getToken) => {
    if (get().syncing) return 0;
    set({ syncing: true });
    let synced = 0;
    try {
      const items = await listPending();
      if (items.length === 0) return 0;
      const token = await getToken();
      for (const item of items) {
        try {
          const result = await createScreening(item.input, token);
          await saveLocalScreening(result);
          await removePending(item.local_id);
          synced += 1;
        } catch {
          break; // still unreachable — keep the rest queued and retry later
        }
      }
      if (synced > 0) set({ lastSyncedAt: Date.now() });
    } finally {
      set({ syncing: false, pendingCount: await countPending() });
    }
    return synced;
  },
}));
