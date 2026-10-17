'use client';

import Link from 'next/link';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { ResultView } from '@/components/screening/ResultView';
import { useScreeningDetail } from '@/hooks/useScreeningDetail';

export function ScreeningDetailClient({ id }: { id: string }) {
  const { data, isLoading } = useScreeningDetail(id);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-4">
        <Alert variant="warning">
          <AlertDescription>
            This screening could not be found. It may not be stored on the server, or it was
            created in a different browser.
          </AlertDescription>
        </Alert>
        <Button asChild variant="outline">
          <Link href="/history">Back to history</Link>
        </Button>
      </div>
    );
  }

  return <ResultView result={data} />;
}
