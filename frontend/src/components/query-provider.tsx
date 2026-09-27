"use client";

import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/client";

/**
 * Server-state cache. A 401 is already handled by the API client (refresh, then
 * sign-out), so retrying it here would only delay the redirect.
 */
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status < 500) return false;
          return failureCount < 1;
        },
      },
    },
  });
}

function QueryProvider({ children }: { children: React.ReactNode }) {
  // One client per browser session; `useState` keeps it stable across renders.
  const [client] = React.useState(makeQueryClient);

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

export { QueryProvider };
