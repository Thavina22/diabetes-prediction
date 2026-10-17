import { Badge } from '@/components/ui/Badge';
import { Card, CardContent } from '@/components/ui/Card';
import { severityBadgeClass } from '@/lib/risk';
import type { ClinicalRule } from '@/lib/types';
import { cn } from '@/lib/utils';

export function RuleCard({ rule }: { rule: ClinicalRule }) {
  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">{rule.metric}</p>
            <p className="text-xs text-muted-foreground">{rule.measurement_type}</p>
          </div>
          <Badge className={cn('border', severityBadgeClass(rule.severity))}>
            {rule.category}
          </Badge>
        </div>

        {rule.value != null && (
          <p className="text-2xl font-bold tabular-nums">{String(rule.value)}</p>
        )}

        <p className="text-sm text-muted-foreground">{rule.interpretation}</p>

        <div className="flex flex-wrap items-center gap-2 pt-1">
          {rule.is_diagnostic && (
            <Badge variant="destructive">Diagnostic range</Badge>
          )}
          {rule.red_flag && <Badge variant="destructive">Red flag</Badge>}
          {rule.requires_confirmation && (
            <Badge variant="outline">Confirmation advised</Badge>
          )}
          {rule.source && (
            <span className="text-xs text-muted-foreground">{rule.source}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
