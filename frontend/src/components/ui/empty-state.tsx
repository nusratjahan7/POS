import * as React from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type EmptyStateProps = React.ComponentProps<"div"> & {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  /** `compact` suits in-card placeholders; `default` suits whole-page regions. */
  size?: "default" | "compact";
};

function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  size = "default",
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      data-size={size}
      className={cn(
        "flex flex-col items-center justify-center text-center",
        size === "default" ? "gap-3 px-6 py-14" : "gap-2.5 px-4 py-8",
        className,
      )}
      {...props}
    >
      {Icon ? (
        <div
          className={cn(
            "bg-muted text-muted-foreground flex items-center justify-center rounded-lg border border-dashed",
            size === "default" ? "size-11" : "size-9",
          )}
        >
          <Icon className={size === "default" ? "size-5" : "size-4"} aria-hidden />
        </div>
      ) : null}

      <div className="flex flex-col gap-1">
        <p className={cn("font-medium", size === "default" ? "text-sm" : "text-xs")}>{title}</p>
        {description ? (
          <p
            className={cn(
              "text-muted-foreground max-w-sm leading-relaxed text-pretty",
              size === "default" ? "text-sm" : "text-xs",
            )}
          >
            {description}
          </p>
        ) : null}
      </div>

      {action ? <div className="mt-1 flex items-center gap-2">{action}</div> : null}
    </div>
  );
}

export { EmptyState };
