import * as React from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** A card framing one chart, with a fixed plot height for `ResponsiveContainer`. */
export function ChartCard({
  title,
  description,
  className,
  children,
}: {
  title: string;
  description?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <div>
          <CardTitle>{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
      </CardHeader>
      <CardContent className={cn("h-72")}>{children}</CardContent>
    </Card>
  );
}

/** Shown inside a chart card when the window has nothing to plot. */
export function ChartEmpty({ message = "Nothing to chart for this period." }: { message?: string }) {
  return (
    <div className="text-muted-foreground flex h-full items-center justify-center text-sm">
      {message}
    </div>
  );
}
