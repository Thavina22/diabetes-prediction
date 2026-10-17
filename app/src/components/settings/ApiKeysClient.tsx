'use client';

import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Badge } from '@/components/ui/Badge';
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from '@/hooks/useApiKeys';

const SCOPES = ['screening:read', 'screening:write', 'history:read', 'export:read'];

export function ApiKeysClient() {
  const { data: keys, isLoading, isError, error } = useApiKeys();
  const createKey = useCreateApiKey();
  const revokeKey = useRevokeApiKey();

  const [name, setName] = React.useState('');
  const [rpm, setRpm] = React.useState(60);
  const [scopes, setScopes] = React.useState<string[]>(['screening:read', 'history:read']);
  const [issued, setIssued] = React.useState<string | null>(null);

  const toggleScope = (scope: string) =>
    setScopes((prev) => (prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || scopes.length === 0) return;
    const res = await createKey.mutateAsync({ name: name.trim(), scopes, rate_limit_rpm: rpm });
    setIssued(res.key);
    setName('');
  };

  const unavailable = isError && (error as { response?: { status?: number } })?.response?.status === 503;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">API keys</CardTitle>
        <CardDescription>Programmatic access for third-party integrations.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {issued && (
          <div className="rounded-md border border-primary/40 bg-primary/5 p-3">
            <p className="text-xs font-medium">Copy this key now — it will not be shown again.</p>
            <code className="mt-1 block break-all font-mono text-xs">{issued}</code>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => navigator.clipboard?.writeText(issued)}
            >
              Copy
            </Button>
          </div>
        )}

        {unavailable && (
          <p className="text-xs text-muted-foreground">
            Connect a database to create and store API keys.
          </p>
        )}

        <form onSubmit={submit} className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="key-name">Name</Label>
            <Input
              id="key-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Clinic integration"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="key-rpm">Rate limit (requests / minute)</Label>
            <Input
              id="key-rpm"
              type="number"
              min={1}
              max={6000}
              value={rpm}
              onChange={(e) => setRpm(Number(e.target.value))}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {SCOPES.map((scope) => (
              <label key={scope} className="flex items-center gap-1.5 text-xs">
                <input
                  type="checkbox"
                  checked={scopes.includes(scope)}
                  onChange={() => toggleScope(scope)}
                />
                {scope}
              </label>
            ))}
          </div>
          <Button type="submit" size="sm" disabled={createKey.isPending || !name.trim()}>
            {createKey.isPending ? 'Creating…' : 'Create key'}
          </Button>
        </form>

        <div className="space-y-2">
          {isLoading && <p className="text-xs text-muted-foreground">Loading keys…</p>}
          {keys?.length === 0 && !unavailable && (
            <p className="text-xs text-muted-foreground">No API keys yet.</p>
          )}
          {keys?.map((key) => (
            <div
              key={key.id}
              className="flex items-center justify-between rounded-md border p-2 text-xs"
            >
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{key.name}</span>
                  <Badge variant="secondary" className="font-mono">
                    {key.key_prefix}…
                  </Badge>
                </div>
                <div className="text-muted-foreground">
                  {key.scopes.join(', ')} · {key.rate_limit_rpm}/min
                  {key.last_used_at ? ` · last used ${new Date(key.last_used_at).toLocaleDateString()}` : ' · never used'}
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={revokeKey.isPending}
                onClick={() => revokeKey.mutate(key.id)}
              >
                Revoke
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
