'use client';

import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export function AuthButtons() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  if (!clerkEnabled) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        Dev mode
      </Badge>
    );
  }

  return (
    <>
      <SignedIn>
        <UserButton afterSignOutUrl="/" />
      </SignedIn>
      <SignedOut>
        <SignInButton mode="modal">
          <Button size="sm">Sign in</Button>
        </SignInButton>
      </SignedOut>
    </>
  );
}
