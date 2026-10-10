import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * A single headline figure. The icon separates one metric from the next at a
 * glance; `accent` lifts the figure the screen is built around; `tone="warning"`
 * marks a figure that needs attention.
 */
export function KpiCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = false,
  tone = "default",
  className,
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: LucideIcon;
  accent?: boolean;
  tone?: "default" | "warning";
  className?: string;
}) {
  return (
    <Card
      className={cn(
        "relative overflow-hidden",
        accent && "border-primary/25 bg-primary/[0.035]",
        className,
      )}
    >
      {accent ? <span aria-hidden className="bg-primary absolute inset-x-0 top-0 h-1" /> : null}
      <CardHeader>
        <div className="flex items-center gap-2.5">
          {Icon ? (
            <span
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-md [&_svg]:size-4",
                tone === "warning"
                  ? "bg-warning/15 text-warning-foreground"
                  : accent
                    ? "bg-primary/10 text-primary"
                    : "bg-muted text-muted-foreground",
              )}
            >
              <Icon aria-hidden />
            </span>
          ) : null}
          <CardTitle className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
            {label}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="text-2xl leading-none font-semibold tracking-tight tabular-nums">{value}</p>
        {hint ? <p className="text-muted-foreground mt-2 text-xs">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}
