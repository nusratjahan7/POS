"use client";

import * as React from "react";

import { AuthProvider } from "@/components/auth/auth-provider";
import { QueryProvider } from "@/components/query-provider";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

/** Client-side context providers shared by every route. */
function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <QueryProvider>
        <TooltipProvider>
          <AuthProvider>
            {children}
            <Toaster />
          </AuthProvider>
        </TooltipProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}

export { Providers };
