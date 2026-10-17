import { Badge } from '@/components/ui/Badge';
import { riskBadgeClass, riskLabel } from '@/lib/risk';
import { cn } from '@/lib/utils';

export function RiskBadge({ category, className }: { category?: string | null; className?: string }) {
  return (
    <Badge className={cn('border', riskBadgeClass(category), className)}>
      {riskLabel(category)}
    </Badge>
  );
}
