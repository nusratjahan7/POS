"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { describeError } from "@/lib/api/client";
import { registerSessionsApi } from "@/lib/api/register-sessions";
import { businessApi } from "@/lib/api/settings";
import { formatDateTime, formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";

function Row({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3",
        strong && "border-t pt-2 font-semibold",
      )}
    >
      <span className={strong ? undefined : "text-muted-foreground"}>{label}</span>
      <span className="tabular-nums">{value}</span>
    </div>
  );
}

/** One shift's reconciliation: the figures, then every drawer movement. */
export function SessionDetailDialog({
  sessionId,
  onClose,
}: {
  sessionId: string;
  onClose: () => void;
}) {
  const businessQuery = useQuery({ queryKey: ["business"], queryFn: () => businessApi.get() });
  const detailQuery = useQuery({
    queryKey: ["register-session-detail", sessionId],
    queryFn: () => registerSessionsApi.get(sessionId),
  });

  const currency = businessQuery.data?.currency ?? "USD";
  const money = (value: string) => formatMoney(value, currency);
  const detail = detailQuery.data;
  const session = detail?.session;
  const summary = detail?.summary;

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[85svh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <DialogTitle>{session ? session.register.name : "Register session"}</DialogTitle>
            {session ? (
              <Badge variant={session.status === "open" ? "success" : "outline"}>
                {session.status === "open" ? "Open" : "Closed"}
              </Badge>
            ) : null}
          </div>
          <DialogDescription>
            {session
              ? `${session.branch.name} · opened ${formatDateTime(session.opened_at)}${
                  session.opened_by ? ` by ${session.opened_by.full_name}` : ""
                }`
              : "Loading the session…"}
          </DialogDescription>
        </DialogHeader>

        {detailQuery.isPending ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : detailQuery.isError || !detail || !session || !summary ? (
          <ErrorState
            title="Could not load the session"
            description={describeError(detailQuery.error)}
          />
        ) : (
          <div className="flex flex-col gap-5">
            <div className="flex flex-col gap-1.5 rounded-md border p-3 text-sm">
              <Row label="Opening cash" value={money(summary.opening_cash)} />
              <Row label="Cash sales" value={money(summary.cash_sales)} />
              <Row label="Cash refunds" value={`− ${money(summary.cash_refunds)}`} />
              <Row label="Cash expenses" value={`− ${money(summary.cash_expenses)}`} />
              <Row label="Cash in" value={money(summary.cash_in)} />
              <Row label="Cash out" value={`− ${money(summary.cash_out)}`} />
              <Row label="Expected in the drawer" value={money(summary.expected_cash)} strong />
              {session.actual_cash !== null ? (
                <>
                  <Row label="Counted (actual)" value={money(session.actual_cash)} />
                  <Row
                    label="Difference"
                    value={money(session.difference ?? "0")}
                    strong
                  />
                </>
              ) : null}
            </div>

            {session.closed_at ? (
              <p className="text-muted-foreground text-xs">
                Closed {formatDateTime(session.closed_at)}
                {session.closed_by ? ` by ${session.closed_by.full_name}` : ""}
                {session.closing_note ? ` · ${session.closing_note}` : ""}
              </p>
            ) : null}

            <div className="flex flex-col gap-2">
              <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                Drawer movements
              </h3>
              {summary.movements.length === 0 ? (
                <p className="text-muted-foreground rounded-md border p-3 text-sm">
                  No cash moved during this session.
                </p>
              ) : (
                <div className="overflow-x-auto rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Note</TableHead>
                        <TableHead>By</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summary.movements.map((movement) => (
                        <TableRow key={movement.id}>
                          <TableCell className="text-muted-foreground text-sm tabular-nums">
                            {formatDateTime(movement.created_at)}
                          </TableCell>
                          <TableCell className="text-sm capitalize">
                            {movement.movement_type.replace("_", " ")}
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {movement.note ?? "—"}
                          </TableCell>
                          <TableCell className="text-sm">
                            {movement.user?.full_name ?? "System"}
                          </TableCell>
                          <TableCell
                            className={cn(
                              "text-right font-medium tabular-nums",
                              Number(movement.amount) < 0 && "text-destructive",
                            )}
                          >
                            {money(movement.amount)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
