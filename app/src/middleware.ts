import {
  NextResponse,
  type NextRequest,
  type NextFetchEvent,
  type NextMiddleware,
} from 'next/server';
import { authMiddleware } from '@clerk/nextjs/server';

const clerkEnabled = Boolean(
  process.env.CLERK_SECRET_KEY && process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
);

let withClerk: NextMiddleware | null = null;
if (clerkEnabled) {
  try {
    withClerk = authMiddleware({
      publicRoutes: ['/', '/sign-in(.*)', '/sign-up(.*)'],
    });
  } catch {
    withClerk = null;
  }
}

export default function middleware(req: NextRequest, event: NextFetchEvent) {
  if (!withClerk) return NextResponse.next();
  return withClerk(req, event);
}

export const config = {
  matcher: [
    '/screening/:path*',
    '/history/:path*',
    '/devices/:path*',
    '/settings/:path*',
  ],
};
