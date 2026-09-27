import type * as React from "react";

import { RequireAuth } from "@/components/auth/guards";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";

/**
 * Application shell: persistent navigation rail plus a scrolling content
 * column. Everything inside requires a live session — the guard redirects to
 * the sign-in screen and remembers where the user was headed.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <div className="flex min-h-svh w-full">
        <AppSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <AppHeader />
          <main className="flex min-w-0 flex-1 flex-col">{children}</main>
        </div>
      </div>
    </RequireAuth>
  );
}
