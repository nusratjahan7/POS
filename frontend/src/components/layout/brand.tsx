import { ScanLine } from "lucide-react";

import { cn } from "@/lib/utils";

/** Wordmark + glyph. The glyph is the only place the brand fills a surface. */
function Brand({ collapsed = false, className }: { collapsed?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5 overflow-hidden", className)}>
      <div className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-md shadow-xs">
        <ScanLine className="size-4.5" aria-hidden />
      </div>
      {collapsed ? null : (
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-sm leading-none font-semibold tracking-tight">POS</span>
          <span className="text-muted-foreground mt-1 truncate text-xs leading-none">
            Point of Sale
          </span>
        </div>
      )}
    </div>
  );
}

export { Brand };
