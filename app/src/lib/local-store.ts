import { openDB, type DBSchema, type IDBPDatabase } from 'idb';
import type { ScreeningResult, HistoryItem, ScreeningInput } from '@/lib/types';

interface StoredScreening {
  id: string;
  created_at: string;
  health_score: number;
  risk_category: string;
  result: ScreeningResult;
}

export interface PendingScreening {
  local_id: string;
  created_at: string;
  input: ScreeningInput;
}

interface DriDB extends DBSchema {
  screenings: {
    key: string;
    value: StoredScreening;
    indexes: { 'by-created': string };
  };
  pending: {
    key: string;
    value: PendingScreening;
    indexes: { 'by-created': string };
  };
}

let dbPromise: Promise<IDBPDatabase<DriDB>> | null = null;

function getDb() {
  if (typeof indexedDB === 'undefined') return null;
  if (!dbPromise) {
    dbPromise = openDB<DriDB>('dri-offline', 2, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('screenings')) {
          const store = db.createObjectStore('screenings', { keyPath: 'id' });
          store.createIndex('by-created', 'created_at');
        }
        if (!db.objectStoreNames.contains('pending')) {
          const pending = db.createObjectStore('pending', { keyPath: 'local_id' });
          pending.createIndex('by-created', 'created_at');
        }
      },
    });
  }
  return dbPromise;
}

function newLocalId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function saveLocalScreening(result: ScreeningResult): Promise<void> {
  const db = await getDb();
  if (!db) return;
  await db.put('screenings', {
    id: result.id,
    created_at: result.created_at,
    health_score: result.health_score,
    risk_category: result.risk_category,
    result,
  });
}

export async function listLocalScreenings(): Promise<HistoryItem[]> {
  const db = await getDb();
  if (!db) return [];
  const all = await db.getAllFromIndex('screenings', 'by-created');
  return all
    .reverse()
    .map((s) => ({
      id: s.id,
      created_at: s.created_at,
      health_score: s.health_score,
      risk_category: s.risk_category,
    }));
}

export async function getLocalScreening(id: string): Promise<ScreeningResult | null> {
  const db = await getDb();
  if (!db) return null;
  const row = await db.get('screenings', id);
  return row?.result ?? null;
}

export async function clearLocalScreenings(): Promise<void> {
  const db = await getDb();
  if (!db) return;
  await db.clear('screenings');
}

// --- Offline queue ---------------------------------------------------------

export async function enqueuePending(input: ScreeningInput): Promise<PendingScreening | null> {
  const db = await getDb();
  if (!db) return null;
  const item: PendingScreening = {
    local_id: newLocalId(),
    created_at: new Date().toISOString(),
    input,
  };
  await db.put('pending', item);
  return item;
}

export async function listPending(): Promise<PendingScreening[]> {
  const db = await getDb();
  if (!db) return [];
  const all = await db.getAllFromIndex('pending', 'by-created');
  return all;
}

export async function countPending(): Promise<number> {
  const db = await getDb();
  if (!db) return 0;
  return db.count('pending');
}

export async function removePending(localId: string): Promise<void> {
  const db = await getDb();
  if (!db) return;
  await db.delete('pending', localId);
}
