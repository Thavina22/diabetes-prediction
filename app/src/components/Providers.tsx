'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ClerkProvider, useAuth } from '@clerk/nextjs';
import { useState, type ReactNode } from 'react';
import { TokenContext, type TokenGetter } from '@/lib/auth-token';

function ClerkTokenBridge({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  const getter: TokenGetter = () => getToken();
  return <TokenContext.Provider value={getter}>{children}</TokenContext.Provider>;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            gcTime: 5 * 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const clerkEnabled = Boolean(clerkKey);

  if (process.env.NODE_ENV === 'development' && !clerkEnabled) {
    // eslint-disable-next-line no-console
    console.warn(
      '[Providers] NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is not set — rendering without auth.'
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      {clerkEnabled ? (
        <ClerkProvider publishableKey={clerkKey}>
          <ClerkTokenBridge>{children}</ClerkTokenBridge>
        </ClerkProvider>
      ) : (
        children
      )}
    </QueryClientProvider>
  );
}
