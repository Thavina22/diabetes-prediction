'use client';

import Link from 'next/link';
import { CalendarClock, Download, FileJson, Share2, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/Alert';
import { Progress } from '@/components/ui/Progress';
import { Separator } from '@/components/ui/Separator';
import { HealthScoreGauge } from '@/components/screening/HealthScoreGauge';
import { RiskBadge } from '@/components/screening/RiskBadge';
import { RuleCard } from '@/components/screening/RuleCard';
import { ShapChart } from '@/components/screening/ShapChart';
import { ScreeningPdfButton } from '@/components/screening/ScreeningPdfButton';
import { downloadExport } from '@/lib/api';
import { useApiToken } from '@/lib/auth-token';
import type { ScreeningResult } from '@/lib/types';

function formatDate(iso: string | undefined) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function ResultView({ result }: { result: ScreeningResult }) {
  const getToken = useApiToken();
  const ml = result.ml_result;
  const mlScore = typeof ml?.risk_score === 'number' ? ml.risk_score : ml?.score;
  const shap = ml?.shap_values as Record<string, number> | null | undefined;

  async function handleServerExport(format: 'fhir' | 'cda') {
    if (!result.id) return;
    try {
      const token = await getToken();
      const blob = await downloadExport(result.id, format, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `screening-${result.id}.${format === 'fhir' ? 'fhir.json' : 'cda.xml'}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // server persistence is required for exports
    }
  }

  return (
    <div className="space-y-6">
      {result.emergency_flags && result.emergency_flags.length > 0 && (
        <Alert variant="destructive">
          <AlertTitle>Immediate attention advised</AlertTitle>
          <AlertDescription>
            {result.emergency_flags.map((f, i) => (
              <div key={i}>
                <strong>{f.type}</strong> — {f.urgency}
                {f.action && f.action.length > 0 && (
                  <ul className="mt-1 list-disc pl-4">
                    {f.action.map((a, j) => (
                      <li key={j}>{a}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="flex flex-col items-center gap-6 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-6">
            <HealthScoreGauge score={result.health_score} />
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <RiskBadge category={result.risk_category} />
                {mlScore != null && (
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <Sparkles className="h-3 w-3" /> ML score {(mlScore * 100).toFixed(1)}%
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                Health score {result.health_score}/100
              </p>
              {result.created_at && (
                <p className="text-xs text-muted-foreground">{formatDate(result.created_at)}</p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <ScreeningPdfButton result={result} />
            <Button variant="outline" size="sm" onClick={() => handleServerExport('fhir')}>
              <FileJson className="mr-2 h-4 w-4" /> FHIR
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleServerExport('cda')}>
              <Share2 className="mr-2 h-4 w-4" /> CDA
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CalendarClock className="h-5 w-5 text-primary" /> Recommended follow-up
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm font-medium">{result.followup_schedule?.when}</p>
          <p className="text-sm text-muted-foreground">{result.followup_schedule?.text}</p>
        </CardContent>
      </Card>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Clinical findings</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {result.glucose_rules?.map((r, i) => <RuleCard key={`glucose-${i}`} rule={r} />)}
          {result.bp_rule && <RuleCard rule={result.bp_rule} />}
          {result.bmi_rule && <RuleCard rule={result.bmi_rule} />}
          {result.lipid_rules?.map((r, i) => <RuleCard key={`lipid-${i}`} rule={r} />)}
        </div>
      </section>

      {shap && Object.keys(shap).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Why this ML score? (SHAP)</CardTitle>
          </CardHeader>
          <CardContent>
            <ShapChart values={shap} />
            <p className="mt-3 text-xs text-muted-foreground">
              Positive values push the model-estimated risk up; negative values push it down.
              This is a statistical estimate, not a diagnosis.
            </p>
          </CardContent>
        </Card>
      )}

      <Separator />

      <div className="flex justify-between">
        <Button asChild variant="ghost">
          <Link href="/screening">
            <Download className="mr-2 h-4 w-4 rotate-180" /> New screening
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/history">View history</Link>
        </Button>
      </div>
    </div>
  );
}
