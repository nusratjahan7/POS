"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/components/auth/auth-provider";
import { Brand } from "@/components/layout/brand";
import { Spinner } from "@/components/ui/spinner";

/**
 * Route guards live on the client because the access token is memory-only —
 * edge/server middleware cannot see it. The refresh cookie is scoped to the
 * API origin, so it is not available to Next.js route handlers either.
 */

export function SessionGate({ message }: { message: string }) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-5">
      <Brand />
      <div className="text-muted-foreground flex items-center gap-2 text-sm">
        <Spinner />
        {message}
      </div>
    </div>
  );
}

/** Only a safe, same-origin target is honoured — `//evil.com` is rejected. */
function safeRedirect(target: string | null): string {
  if (target && target.startsWith("/") && !target.startsWith("//")) return target;
  return "/";
}

/** Blocks a route until a session exists, then remembers where to return. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (status !== "unauthenticated") return;
    // Preserve the current location so login can bounce the user back.
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    router.replace(`/login?next=${next}`);
  }, [status, router]);

  if (status !== "authenticated") {
    return <SessionGate message="Restoring your session" />;
  }

  return <>{children}</>;
}

/** Keeps signed-in users away from the login and forgot-password screens. */
export function GuestOnly({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = safeRedirect(searchParams.get("next"));

  React.useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, next, router]);

  // Deliberately unguarded: a signed-out visitor sees the form immediately
  // instead of waiting on a spinner. Someone already signed in gets redirected
  // a moment later, which is the far rarer case.
  return <>{children}</>;
}
