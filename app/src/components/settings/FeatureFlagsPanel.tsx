'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useFeatureFlags } from '@/hooks/useFeatureFlags';

export function FeatureFlagsPanel() {
  const { flags, isLoading } = useFeatureFlags();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Features</CardTitle>
        <CardDescription>Capabilities enabled for your account.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading && <p className="text-xs text-muted-foreground">Loading…</p>}
        {flags.map((flag) => (
          <div key={flag.key} className="flex items-start justify-between gap-3 text-xs">
            <div>
              <div className="font-medium">{flag.key}</div>
              <div className="text-muted-foreground">{flag.description}</div>
            </div>
            <Badge variant={flag.enabled ? 'default' : 'outline'}>
              {flag.enabled
                ? flag.rollout_percentage >= 100
                  ? 'on'
                  : `${flag.rollout_percentage}%`
                : 'off'}
            </Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
