import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** A single headline figure on a report tab. */
export function KpiCard({
  label,
  value,
  hint,
  className,
}: {
  label: string;
  value: string;
  hint?: string;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="text-2xl leading-none font-semibold tracking-tight tabular-nums">{value}</p>
        {hint ? <p className="text-muted-foreground mt-2 text-xs">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}
