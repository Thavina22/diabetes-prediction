'use client';

import { usePathname } from 'next/navigation';
import { Sidebar } from '@/components/dashboard/Sidebar';
import { AuthButtons } from '@/components/auth/AuthButtons';
import { OfflineSyncManager } from '@/components/pwa/OfflineSyncManager';

const TITLES: Record<string, string> = {
  '/screening': 'New screening',
  '/history': 'Screening history',
  '/devices': 'Connected devices',
  '/settings': 'Settings',
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const title =
    TITLES[pathname] ??
    (Object.entries(TITLES).find(([k]) => pathname.startsWith(`${k}/`))?.[1] ??
      'Dashboard');

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
          <h1 className="text-base font-semibold">{title}</h1>
          <AuthButtons />
        </header>
        <main className="flex-1 bg-muted/30 p-6">
          <div className="mx-auto w-full max-w-5xl">{children}</div>
        </main>
      </div>
      <OfflineSyncManager />
    </div>
  );
}
