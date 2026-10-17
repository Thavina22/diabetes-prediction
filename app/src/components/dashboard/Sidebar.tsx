'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  ClipboardPlus,
  History,
  Smartphone,
  Settings,
  BookOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/screening', label: 'New screening', icon: ClipboardPlus },
  { href: '/history', label: 'History', icon: History },
  { href: '/devices', label: 'Devices', icon: Smartphone },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 border-r bg-card md:flex md:flex-col">
      <Link href="/" className="flex items-center gap-2 border-b px-5 py-4">
        <Activity className="h-5 w-5 text-primary" />
        <span className="text-sm font-semibold leading-tight">
          Diabetes Risk
          <br />
          Intelligence
        </span>
      </Link>

      <nav className="flex-1 space-y-1 p-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <a
        href={`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/docs`}
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-3 border-t px-5 py-4 text-xs text-muted-foreground hover:text-foreground"
      >
        <BookOpen className="h-4 w-4" />
        API documentation
      </a>
    </aside>
  );
}
