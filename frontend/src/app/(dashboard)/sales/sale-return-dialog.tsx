"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { salesApi, type Sale, type SaleReturn } from "@/lib/api/sales";
import { paymentMethodsApi } from "@/lib/api/settings";
import { formatAmount, formatQuantity } from "@/lib/format";
import { planReturn, remainingQuantity, splitRefund, type ReturnableLine } from "@/lib/sales/returns";

/** Fold a sale's return history into per-line "already came back" totals. */
function returnableLines(sale: Sale, returns: SaleReturn[]): ReturnableLine[] {
  const history = new Map<string, { quantity: number; amount: number }>();
  for (const record of returns) {
    if (record.status !== "completed") continue;
    for (const item of record.items) {
      const current = history.get(item.sale_item_id) ?? { quantity: 0, amount: 0 };
      history.set(item.sale_item_id, {
        quantity: current.quantity + Number(item.quantity),
        amount: current.amount + Number(item.line_total),
      });
    }
  }

  return sale.items.map((item) => {
    const past = history.get(item.id) ?? { quantity: 0, amount: 0 };
    return {
      saleItemId: item.id,
      productName: item.product_name,
      sku: item.sku,
      unitPrice: Number(item.unit_price),
      sold: Number(item.quantity),
      returned: past.quantity,
      lineTotal: Number(item.line_total),
      alreadyRefunded: past.amount,
    };
  });
}

/**
 * Hand goods back from one sale: pick the lines and quantities, say why and how
 * the refund is settled, and confirm. The server restocks, refunds and updates
 * the sale in one transaction; the figures here are a live preview of it.
 */
export function SaleReturnDialog({
  sale,
  onClose,
  onReturned,
}: {
  sale: Sale;
  onClose: () => void;
  onReturned: () => void;
}) {
  const queryClient = useQueryClient();
  const [quantities, setQuantities] = React.useState<Record<string, string>>({});
  const [reason, setReason] = React.useState("");
  const [methodId, setMethodId] = React.useState("");
  const [reference, setReference] = React.useState("");

  const returnsQuery = useQuery({
    queryKey: ["sale-returns", sale.id],
    queryFn: () => salesApi.listReturns(sale.id),
  });
  const methodsQuery = useQuery({
    queryKey: ["payment-methods", "options"],
    queryFn: () => paymentMethodsApi.options(),
  });

  const money = (value: string | number) => formatAmount(value);
  const methods = methodsQuery.data ?? [];

  const lines = React.useMemo(
    () => returnableLines(sale, returnsQuery.data ?? []),
    [sale, returnsQuery.data],
  );

  const selections = React.useMemo(() => {
    const chosen: Record<string, number> = {};
    for (const [key, value] of Object.entries(quantities)) {
      const parsed = Number(value);
      if (Number.isFinite(parsed) && parsed > 0) chosen[key] = parsed;
    }
    return chosen;
  }, [quantities]);

  const remainingRefundable = Math.max(
    Number(sale.total) - Number(sale.returned_amount ?? 0),
    0,
  );
  const plan = planReturn(lines, selections, remainingRefundable);
  const split = splitRefund(plan.total, Number(sale.due), Number(sale.returned_amount ?? 0));

  const selectedMethod = methods.find((method) => method.id === methodId);
  const blocking =
    plan.lines.length === 0
      ? "Choose how many units are coming back."
      : split.cash > 0 && !methodId
        ? "Choose how the cash part of the refund is settled."
        : selectedMethod?.requires_reference && !reference.trim()
          ? `${selectedMethod.name} needs a reference.`
          : null;

  const mutation = useMutation({
    mutationFn: () =>
      salesApi.createReturn(sale.id, {
        items: plan.lines.map((line) => ({
          sale_item_id: line.saleItemId,
          quantity: String(line.quantity),
        })),
        reason: reason.trim() || null,
        payment_method_id: methodId || null,
        reference: reference.trim() || null,
      }),
    onSuccess: (record) => {
      toast.success(`${record.return_number} recorded · refunded ${money(record.refund_amount)}`);
      void queryClient.invalidateQueries({ queryKey: ["sale-returns", sale.id] });
      onReturned();
      onClose();
    },
    onError: (cause) => toast.error(describeError(cause)),
  });

  const nothingReturnable = lines.every((line) => remainingQuantity(line) <= 0);

  return (
    <Dialog open onOpenChange={(next) => !next && !mutation.isPending && onClose()}>
      <DialogContent className="max-h-[85svh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RotateCcw className="size-4" aria-hidden />
            Return goods
          </DialogTitle>
          <DialogDescription>
            From <span className="font-mono">{sale.sale_number}</span>. The server restocks the
            units, refunds them and updates the sale in one step.
          </DialogDescription>
        </DialogHeader>

        {returnsQuery.isPending ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : returnsQuery.isError ? (
          <ErrorState
            title="Could not load this sale's returns"
            description={describeError(returnsQuery.error)}
            action={
              <Button variant="outline" onClick={() => void returnsQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : nothingReturnable ? (
          <p className="text-muted-foreground text-sm">
            Everything on this sale has already been returned.
          </p>
        ) : (
          <div className="flex flex-col gap-5">
            <div className="overflow-x-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Item</TableHead>
                    <TableHead className="text-right">Sold</TableHead>
                    <TableHead className="text-right">Returned</TableHead>
                    <TableHead className="text-right">Can return</TableHead>
                    <TableHead className="w-28 text-right">Return now</TableHead>
                    <TableHead className="text-right">Refund</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lines.map((line) => {
                    const remaining = remainingQuantity(line);
                    const planned = plan.lines.find(
                      (entry) => entry.saleItemId === line.saleItemId,
                    );
                    return (
                      <TableRow key={line.saleItemId}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{line.productName}</span>
                            <span className="text-muted-foreground text-xs">{line.sku}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatQuantity(line.sold)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatQuantity(line.returned)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatQuantity(remaining)}
                        </TableCell>
                        <TableCell>
                          <Input
                            inputMode="decimal"
                            value={quantities[line.saleItemId] ?? ""}
                            onChange={(event) =>
                              setQuantities((current) => ({
                                ...current,
                                [line.saleItemId]: event.target.value,
                              }))
                            }
                            placeholder="0"
                            disabled={remaining <= 0}
                            aria-label={`Quantity of ${line.productName} to return`}
                            className="text-right tabular-nums"
                          />
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {planned ? money(planned.refund) : "—"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            <div className="flex flex-col gap-1 rounded-md border p-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Value of goods returned</span>
                <span className="tabular-nums">{money(plan.total)}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Clears outstanding balance</span>
                <span className="tabular-nums">{money(split.credited)}</span>
              </div>
              <div className="flex items-center justify-between gap-3 border-t pt-2 font-semibold">
                <span>Refunded to customer</span>
                <span className="tabular-nums">{money(split.cash)}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Reason" htmlFor="return-reason" hint="Recorded on the return.">
                <Input
                  id="return-reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="e.g. damaged, wrong size"
                  autoComplete="off"
                />
              </Field>
              <Field
                label="Refund method"
                htmlFor="return-method"
                hint={split.cash > 0 ? "How the cash part is paid back." : "Nothing is paid out."}
              >
                <Select value={methodId} onValueChange={setMethodId}>
                  <SelectTrigger id="return-method" aria-label="Refund method">
                    <SelectValue placeholder="Choose a method" />
                  </SelectTrigger>
                  <SelectContent>
                    {methods.map((method) => (
                      <SelectItem key={method.id} value={method.id}>
                        {method.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            {selectedMethod?.requires_reference ? (
              <Field
                label="Reference"
                htmlFor="return-reference"
                hint={`${selectedMethod.name} needs its transaction reference.`}
              >
                <Input
                  id="return-reference"
                  value={reference}
                  onChange={(event) => setReference(event.target.value)}
                  placeholder="e.g. approval code"
                  autoComplete="off"
                />
              </Field>
            ) : null}

            {blocking ? <p className="text-warning-foreground text-sm">{blocking}</p> : null}
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={Boolean(blocking) || mutation.isPending || nothingReturnable}
          >
            {mutation.isPending ? "Recording…" : "Confirm return"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
