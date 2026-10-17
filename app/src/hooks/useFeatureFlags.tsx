'use client';

import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getFeatureFlags } from '@/lib/api';
import type { FeatureFlag } from '@/lib/types';

export function useFeatureFlags() {
  const query = useQuery({
    queryKey: ['feature-flags'],
    queryFn: getFeatureFlags,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const flags = query.data?.flags ?? [];
  const enabled = (key: string) => flags.find((f) => f.key === key)?.enabled ?? false;

  return { ...query, flags, enabled };
}

/** Render children only when the flag is enabled. */
export function FeatureGate({
  flag,
  flags,
  fallback = null,
  children,
}: {
  flag: string;
  flags: FeatureFlag[];
  fallback?: ReactNode;
  children: ReactNode;
}) {
  const isOn = flags.find((f) => f.key === flag)?.enabled ?? false;
  return <>{isOn ? children : fallback}</>;
}
