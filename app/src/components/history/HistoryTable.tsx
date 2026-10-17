'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import { RiskBadge } from '@/components/screening/RiskBadge';
import { useHistory } from '@/hooks/useHistory';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 10;

export function HistoryTable() {
  const [risk, setRisk] = useState<string>('all');
  const [page, setPage] = useState(0);

  const { data, isLoading, isError } = useHistory({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    risk_category: risk === 'all' ? undefined : risk,
  });

  const total = data?.total ?? 0;
  const rows = data?.screenings ?? [];
  const maxPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {isLoading ? 'Loading…' : `${total} screening${total === 1 ? '' : 's'}`}
        </p>
        <div className="w-48">
          <Select
            value={risk}
            onValueChange={(v) => {
              setRisk(v);
              setPage(0);
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Filter by risk" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All risk levels</SelectItem>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Moderate</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="very_high">Very high</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {isError && (
        <Alert variant="warning">
          <AlertDescription>Could not load history. Showing nothing.</AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No screenings yet.{' '}
            <Link href="/screening" className="text-primary underline">
              Run your first screening
            </Link>
            .
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {rows.map((row) =>
            row.pending ? (
              <Card key={row.id} className="border-dashed">
                <CardContent className="flex items-center justify-between p-4">
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      {new Date(row.created_at).toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Waiting to sync from this device
                    </p>
                  </div>
                  <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                    Pending sync
                  </span>
                </CardContent>
              </Card>
            ) : (
              <Link key={row.id} href={`/history/${row.id}`} className="block">
                <Card className={cn('transition-colors hover:bg-accent/50')}>
                  <CardContent className="flex items-center justify-between p-4">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        {new Date(row.created_at).toLocaleString()}
                      </p>
                      <p className="text-xs text-muted-foreground">ID {row.id.slice(0, 8)}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-lg font-semibold tabular-nums">
                        {row.health_score}
                        <span className="text-xs text-muted-foreground">/100</span>
                      </span>
                      <RiskBadge category={row.risk_category} />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            )
          )}
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="text-xs text-muted-foreground">
            Page {page + 1} of {maxPage + 1}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= maxPage}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
