'use client';

import { useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { toast } from '@/components/ui/use-toast';
import type { ScreeningResult } from '@/lib/types';

export function ScreeningPdfButton({ result }: { result: ScreeningResult }) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    setLoading(true);
    try {
      const { generateScreeningPdf } = await import('./pdf-generate');
      const blob = await generateScreeningPdf(result);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `screening-${result.id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast({
        variant: 'destructive',
        title: 'PDF export failed',
        description: e instanceof Error ? e.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button size="sm" onClick={handleClick} disabled={loading}>
      {loading ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <FileText className="mr-2 h-4 w-4" />
      )}
      PDF
    </Button>
  );
}
