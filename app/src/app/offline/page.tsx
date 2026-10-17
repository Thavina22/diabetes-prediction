import Link from 'next/link';

export const metadata = {
  title: 'Offline — Diabetes Risk Intelligence',
};

export default function OfflinePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-2xl font-bold text-white">
        DRI
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">You&apos;re offline</h1>
        <p className="max-w-md text-muted-foreground">
          Your connection dropped. You can still start a new screening — it will be
          saved on this device and synced automatically once you&apos;re back online.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          href="/screening"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          New Screening
        </Link>
        <Link
          href="/history"
          className="rounded-md border px-4 py-2 text-sm font-medium"
        >
          Cached History
        </Link>
      </div>
    </main>
  );
}
