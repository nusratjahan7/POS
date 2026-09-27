import Link from "next/link";
import { Compass } from "lucide-react";

import { Brand } from "@/components/layout/brand";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

export default function NotFound() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-8 p-6">
      <Brand />
      <div className="w-full max-w-lg border-b" aria-hidden />
      <EmptyState
        className="px-0 py-0"
        icon={Compass}
        title="Page not found"
        description="The page you were looking for does not exist or has moved."
        action={
          <Button asChild variant="outline">
            <Link href="/">Back to dashboard</Link>
          </Button>
        }
      />
    </div>
  );
}
