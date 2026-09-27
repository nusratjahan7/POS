import * as React from "react";
import { AlertTriangle } from "lucide-react";

import { cn } from "@/lib/utils";

type ErrorStateProps = React.ComponentProps<"div"> & {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  /** Rendered under the description — wire this to `error.digest` in dev. */
  detail?: string;
  size?: "default" | "compact";
};

function ErrorState({
  title = "Something went wrong",
  description = "The request could not be completed. Try again, or contact support if the problem persists.",
  action,
  detail,
  size = "default",
  className,
  ...props
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      data-slot="error-state"
      data-size={size}
      className={cn(
        "flex flex-col items-center justify-center text-center",
        size === "default" ? "gap-3 px-6 py-14" : "gap-2.5 px-4 py-8",
        className,
      )}
      {...props}
    >
      <div
        className={cn(
          "bg-destructive/10 text-destructive flex items-center justify-center rounded-lg border border-dashed border-destructive/30",
          size === "default" ? "size-11" : "size-9",
        )}
      >
        <AlertTriangle className={size === "default" ? "size-5" : "size-4"} aria-hidden />
      </div>

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
        {detail ? (
          <p className="text-muted-foreground/70 mt-1 font-mono text-xs break-all">{detail}</p>
        ) : null}
      </div>

      {action ? <div className="mt-1 flex items-center gap-2">{action}</div> : null}
    </div>
  );
}

export { ErrorState };
