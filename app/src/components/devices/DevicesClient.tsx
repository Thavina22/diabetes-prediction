'use client';

import { RefreshCw, Smartphone, Trash2, Watch } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  useConnectDevice,
  useDevices,
  useDisconnectDevice,
  useSyncDevice,
} from '@/hooks/useDevices';

const PROVIDERS = [
  { id: 'apple_health', name: 'Apple Health', detail: 'iPhone / Apple Watch glucose & BP', icon: Watch },
  { id: 'google_fit', name: 'Google Fit', detail: 'Android Health Connect data', icon: Smartphone },
  { id: 'dexcom', name: 'Dexcom CGM', detail: 'Continuous glucose readings', icon: Watch },
  { id: 'libre', name: 'FreeStyle Libre', detail: 'Continuous glucose readings', icon: Watch },
];

export function DevicesClient() {
  const { data, isLoading, isError } = useDevices();
  const connect = useConnectDevice();
  const disconnect = useDisconnectDevice();
  const sync = useSyncDevice();

  const connected = new Map((data ?? []).map((d) => [d.provider, d]));

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Connected devices</h2>

      {isError && (
        <Alert variant="warning">
          <AlertDescription>
            Couldn&apos;t reach the device service. Connect a database to enable syncing.
          </AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : (
        PROVIDERS.map((p) => {
          const Icon = p.icon;
          const existing = connected.get(p.id);
          return (
            <Card key={p.id}>
              <CardContent className="flex items-center justify-between gap-4 p-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    <Icon className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-sm font-medium">{p.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {existing
                        ? `Last synced ${
                            existing.last_sync_at
                              ? new Date(existing.last_sync_at).toLocaleString()
                              : 'never'
                          }`
                        : p.detail}
                    </p>
                  </div>
                </div>

                {existing ? (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={sync.isPending && sync.variables === existing.id}
                      onClick={() => sync.mutate(existing.id)}
                    >
                      <RefreshCw
                        className={`mr-2 h-3.5 w-3.5 ${
                          sync.isPending && sync.variables === existing.id ? 'animate-spin' : ''
                        }`}
                      />
                      Sync
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={disconnect.isPending}
                      onClick={() => disconnect.mutate(existing.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={connect.isPending}
                    onClick={() => connect.mutate({ provider: p.id })}
                  >
                    Connect
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })
      )}

      <p className="text-xs text-muted-foreground">
        Apple HealthKit requires an iOS entitlement; Google Fit uses Health Connect. Connectors
        store encrypted tokens and pull readings on demand or via the daily Vercel Cron job.
      </p>
    </div>
  );
}
