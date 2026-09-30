"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";

import { PickedDateRange, SalesDateRange } from "@/app/(dashboard)/sales/sales-date-range";
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
import type { LedgerParams, LedgerStatement } from "@/lib/api/ledger";
import { businessApi } from "@/lib/api/settings";
import { formatDateTime, formatMoney } from "@/lib/format";

type LedgerDialogProps = {
  title: string;
  description: string;
  /** Stable prefix so React Query caches each party's statement separately. */
  cacheKey: string;
  fetchStatement: (params: LedgerParams) => Promise<LedgerStatement>;
  onClose: () => void;
};

/** Serialises the picked range to the `YYYY-MM-DD` the API expects. */
function isoDay(value: PickedDateRange["start"] | undefined): string | undefined {
  return value ? value.toString().slice(0, 10) : undefined;
}

/**
 * An account statement: every movement in date order with a running balance,
 * filterable by date range. The figures come straight from the server, which
 * derives them from the same rows that move the account balance.
 */
export function LedgerDialog({
  title,
  description,
  cacheKey,
  fetchStatement,
  onClose,
}: LedgerDialogProps) {
  const [range, setRange] = React.useState<PickedDateRange | null>(null);
  const dateFrom = isoDay(range?.start);
  const dateTo = isoDay(range?.end);

  const businessQuery = useQuery({ queryKey: ["business"], queryFn: () => businessApi.get() });
  const ledgerQuery = useQuery({
    queryKey: ["ledger", cacheKey, dateFrom ?? null, dateTo ?? null],
    queryFn: () => fetchStatement({ date_from: dateFrom, date_to: dateTo }),
  });

  const currency = businessQuery.data?.currency ?? "USD";
  const statement = ledgerQuery.data;
  const money = (value: string) => formatMoney(value, currency);
  const side = (value: string) => (Number(value) > 0 ? money(value) : "—");

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[85svh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BookOpen className="size-4" aria-hidden />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <SalesDateRange value={range} onChange={setRange} />

          {ledgerQuery.isPending ? (
            <div className="flex flex-col gap-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : ledgerQuery.isError || !statement ? (
            <ErrorState
              title="Could not load the statement"
              description={describeError(ledgerQuery.error)}
            />
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border p-3">
                  <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                    Opening balance
                  </div>
                  <div className="mt-1 text-lg font-semibold tabular-nums">
                    {money(statement.opening_balance)}
                  </div>
                </div>
                <div className="rounded-lg border p-3">
                  <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                    Closing balance
                  </div>
                  <div className="mt-1 text-lg font-semibold tabular-nums">
                    {money(statement.closing_balance)}
                  </div>
                </div>
              </div>

              {statement.entries.length === 0 ? (
                <p className="text-muted-foreground rounded-md border p-3 text-sm">
                  No account activity for this period.
                </p>
              ) : (
                <div className="overflow-x-auto rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Reference</TableHead>
                        <TableHead className="text-right">Debit</TableHead>
                        <TableHead className="text-right">Credit</TableHead>
                        <TableHead className="text-right">Balance</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {statement.entries.map((entry, index) => (
                        <TableRow key={`${entry.entry_type}-${entry.reference}-${index}`}>
                          <TableCell className="text-muted-foreground text-sm tabular-nums">
                            {formatDateTime(entry.occurred_at)}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-col">
                              <span className="font-mono text-xs font-medium">
                                {entry.reference}
                              </span>
                              {entry.description ? (
                                <span className="text-muted-foreground text-xs">
                                  {entry.description}
                                </span>
                              ) : null}
                            </div>
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {side(entry.debit)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {side(entry.credit)}
                          </TableCell>
                          <TableCell className="text-right font-medium tabular-nums">
                            {money(entry.balance)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
