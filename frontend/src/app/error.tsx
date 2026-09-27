"use client";

import { RotateCcw } from "lucide-react";

import { Brand } from "@/components/layout/brand";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";

/** Route-level error boundary. Renders outside the shell, so it stands alone. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-8 p-6">
      <Brand />
      <div className="border-b w-full max-w-lg" aria-hidden />
      <ErrorState
        className="px-0 py-0"
        title="This page could not be rendered"
        description="An unexpected error interrupted the request. Retrying is safe — no data was changed."
        detail={error.digest ? `Reference: ${error.digest}` : undefined}
        action={
          <Button onClick={reset} variant="outline">
            <RotateCcw className="size-4" />
            Try again
          </Button>
        }
      />
    </div>
  );
}
