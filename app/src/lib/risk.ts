import type { RiskCategory } from '@/lib/types';

export const RISK_LABELS: Record<string, string> = {
  low: 'Low risk',
  medium: 'Moderate risk',
  high: 'High risk',
  very_high: 'Very high risk',
};

export const RISK_BADGE_CLASSES: Record<string, string> = {
  low: 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200',
  medium: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-200',
  very_high: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-200',
};

export const RISK_HEX: Record<string, string> = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#f97316',
  very_high: '#ef4444',
};

export const SEVERITY_BADGE_CLASSES: Record<string, string> = {
  normal: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  low: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  borderline: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  elevated: 'bg-amber-100 text-amber-800 border-amber-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  critical: 'bg-red-100 text-red-800 border-red-200',
  emergency: 'bg-red-600 text-white border-red-700',
};

export function riskLabel(category?: string | null): string {
  if (!category) return 'Unknown';
  return RISK_LABELS[category] ?? category;
}

export function riskBadgeClass(category?: string | null): string {
  if (!category) return 'bg-muted text-muted-foreground border-border';
  return RISK_BADGE_CLASSES[category] ?? 'bg-muted text-muted-foreground border-border';
}

export function riskHex(category?: string | null): string {
  if (!category) return '#94a3b8';
  return RISK_HEX[category] ?? '#94a3b8';
}

export function severityBadgeClass(severity?: string | null): string {
  if (!severity) return 'bg-muted text-muted-foreground border-border';
  return SEVERITY_BADGE_CLASSES[severity] ?? 'bg-muted text-muted-foreground border-border';
}

export interface ScoreBand {
  label: string;
  color: string;
}

export function scoreBand(score: number): ScoreBand {
  if (score >= 80) return { label: 'Excellent', color: '#10b981' };
  if (score >= 60) return { label: 'Good', color: '#22c55e' };
  if (score >= 40) return { label: 'Needs attention', color: '#f59e0b' };
  return { label: 'Poor', color: '#ef4444' };
}

export function isRiskCategory(value: string): value is RiskCategory {
  return ['low', 'medium', 'high', 'very_high'].includes(value);
}
