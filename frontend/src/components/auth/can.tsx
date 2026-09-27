"use client";

import * as React from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { hasPermission } from "@/lib/auth/permissions";

/**
 * Presentation-only permission gate.
 *
 * IMPORTANT: hiding a control is not authorization. Every sensitive endpoint
 * enforces the same permission server-side through `require_permissions`, so a
 * caller who bypasses this component is still refused. This exists purely so
 * users are not offered actions that would fail.
 */
function Can({
  permission,
  children,
  fallback = null,
}: {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { user } = useAuth();
  return hasPermission(user, permission) ? <>{children}</> : <>{fallback}</>;
}

/** Imperative form of {@link Can}, for conditional props rather than rendering. */
function useCan(permission: string): boolean {
  const { user } = useAuth();
  return hasPermission(user, permission);
}

export { Can, useCan };
