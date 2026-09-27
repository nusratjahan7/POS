"use client";

import * as React from "react";

import { authApi, type AuthUser } from "@/lib/api/auth";
import { onSessionExpired, refreshSession } from "@/lib/api/client";
import { tokenStore } from "@/lib/auth/token-store";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<AuthStatus>("loading");
  const [user, setUser] = React.useState<AuthUser | null>(null);

  const clearSession = React.useCallback(() => {
    tokenStore.clear();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  // Session restoration. The access token is memory-only, so after a reload the
  // only way to learn whether we are still signed in is the refresh cookie.
  React.useEffect(() => {
    let cancelled = false;

    void (async () => {
      const session = await refreshSession();
      if (cancelled) return;
      if (session) {
        setUser(session.user as AuthUser);
        setStatus("authenticated");
      } else {
        setStatus("unauthenticated");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // A refresh that fails mid-session means the session is over (expired,
  // revoked by a password change elsewhere, or the token family was rotated).
  React.useEffect(() => {
    onSessionExpired(clearSession);
    return () => onSessionExpired(null);
  }, [clearSession]);

  const login = React.useCallback(async (email: string, password: string) => {
    const result = await authApi.login(email, password);
    tokenStore.set(result.access_token);
    setUser(result.user);
    setStatus("authenticated");
    return result.user;
  }, []);

  const logout = React.useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Revoking server-side failed (offline, already expired). Local state is
      // still cleared: the user asked to sign out and must end up signed out.
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const changePassword = React.useCallback(
    async (currentPassword: string, newPassword: string) => {
      await authApi.changePassword(currentPassword, newPassword);
      // The backend revokes every session on a password change, this one
      // included, so the user is expected to sign in again.
      clearSession();
    },
    [clearSession],
  );

  const refreshUser = React.useCallback(async () => {
    setUser(await authApi.me());
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({ status, user, login, logout, changePassword, refreshUser }),
    [status, user, login, logout, changePassword, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>.");
  }
  return context;
}
