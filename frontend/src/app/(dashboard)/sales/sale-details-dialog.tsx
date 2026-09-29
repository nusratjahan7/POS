"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Printer, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { Can } from "@/components/auth/can";
import { InvoicePreviewDialog } from "@/components/invoice/invoice-preview-dialog";
import { PaymentStatusBadge, SaleStatusBadge } from "@/components/sales/status-badge";
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
import { salesApi } from "@/lib/api/sales";
import { formatDateTime, formatMoney, formatQuantity } from "@/lib/format";

function Row({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: React.ReactNode;
  strong?: boolean;
}) {
  return (
    <div
      className={
        strong
          ? "flex items-center justify-between gap-3 border-t pt-2 text-base font-semibold"
          : "flex items-center justify-between gap-3 text-sm"
      }
    >
      <span className={strong ? undefined : "text-muted-foreground"}>{label}</span>
      <span className="tabular-nums">{value}</span>
    </div>
  );
}

/**
 * One sale in full: its invoice details, lines, tenders, totals and timestamps,
 * with the receipt actions (print / reprint) and the refund reversal.
 *
 * Fetches the same receipt payload the print view uses, so the two share one
 * cache entry and cost one request between them.
 */
export function SaleDetailsDialog({
  saleId,
  onClose,
  onChanged,
}: {
  saleId: string;
  onClose: () => void;
  onChanged: () => void;
}) {
  const queryClient = useQueryClient();
  const [printOpen, setPrintOpen] = React.useState(false);
  const [refundOpen, setRefundOpen] = React.useState(false);
  const [reason, setReason] = React.useState("");

  const receiptQuery = useQuery({
    queryKey: ["sale-receipt", saleId],
    queryFn: () => salesApi.receipt(saleId),
  });
  const receipt = receiptQuery.data;
  const sale = receipt?.sale;
  const currency = receipt?.business.currency ?? "USD";
  const money = (value: string | number | null | undefined) => formatMoney(value, currency);

  const refundMutation = useMutation({
    mutationFn: () => salesApi.refund(saleId, { reason: reason.trim() || null }),
    onSuccess: (updated) => {
      toast.success(`${updated.sale_number} refunded`);
      setRefundOpen(false);
      setReason("");
      void queryClient.invalidateQueries({ queryKey: ["sale-receipt", saleId] });
      onChanged();
    },
    onError: (cause) => toast.error(describeError(cause)),
  });

  const refundable = sale?.status === "completed";

  return (
    <>
      <Dialog open onOpenChange={(next) => !next && onClose()}>
        <DialogContent className="max-h-[85svh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <div className="flex flex-wrap items-center gap-2">
              <DialogTitle className="font-mono">{sale?.sale_number ?? "Sale"}</DialogTitle>
              {sale ? <SaleStatusBadge status={sale.status} /> : null}
              {sale ? <PaymentStatusBadge sale={sale} /> : null}
            </div>
            <DialogDescription>
              {receipt
                ? `${receipt.business.name} · ${receipt.branch.name}`
                : "Loading the sale…"}
            </DialogDescription>
          </DialogHeader>

          {receiptQuery.isPending ? (
            <div className="flex flex-col gap-3">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-40 w-full" />
              <Skeleton className="h-24 w-2/3 self-end" />
            </div>
          ) : receiptQuery.isError || !sale ? (
            <ErrorState
              title="Could not load the sale"
              description={describeError(receiptQuery.error)}
              action={
                <Button variant="outline" onClick={() => void receiptQuery.refetch()}>
                  Try again
                </Button>
              }
            />
          ) : (
            <div className="flex flex-col gap-5">
              <div className="grid grid-cols-1 gap-2 rounded-md border p-3 sm:grid-cols-2">
                <Row label="Date" value={formatDateTime(sale.sold_at)} />
                <Row label="Cashier" value={sale.cashier?.full_name ?? "—"} />
                <Row label="Customer" value={sale.customer?.name ?? "Walk-in"} />
                <Row label="Branch" value={receipt.branch.name} />
              </div>

              <div className="overflow-x-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Discount</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sale.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{item.product_name}</span>
                            <span className="text-muted-foreground text-xs">{item.sku}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatQuantity(item.quantity)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {money(item.unit_price)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {Number(item.discount) > 0 ? `-${money(item.discount)}` : "—"}
                        </TableCell>
                        <TableCell className="text-right font-medium tabular-nums">
                          {money(item.line_total)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="flex flex-col gap-1 rounded-md border p-3">
                <Row label="Subtotal" value={money(sale.subtotal)} />
                {Number(sale.discount) > 0 ? (
                  <Row label="Discount" value={`-${money(sale.discount)}`} />
                ) : null}
                {Number(sale.tax) > 0 ? (
                  <Row label={receipt.business.tax_label} value={money(sale.tax)} />
                ) : null}
                <Row label="Total" value={money(sale.total)} strong />
                <Row label="Paid" value={money(sale.paid)} />
                {Number(sale.change_amount) > 0 ? (
                  <Row label="Change" value={money(sale.change_amount)} />
                ) : null}
                {Number(sale.due) > 0 ? <Row label="Due" value={money(sale.due)} strong /> : null}
              </div>

              <div className="flex flex-col gap-2">
                <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                  Payments
                </h3>
                <div className="flex flex-col gap-1 rounded-md border p-3">
                  {sale.payments.map((payment) => (
                    <Row
                      key={payment.id}
                      label={
                        payment.reference
                          ? `${payment.payment_method.name} · ${payment.reference}`
                          : payment.payment_method.name
                      }
                      value={money(payment.amount)}
                    />
                  ))}
                </div>
              </div>

              <div className="flex flex-col gap-1 rounded-md border p-3">
                <Row label="Sold" value={formatDateTime(sale.sold_at)} />
                <Row label="Created" value={formatDateTime(sale.created_at)} />
                {sale.refunded_at ? (
                  <>
                    <Row label="Refunded" value={formatDateTime(sale.refunded_at)} />
                    <Row label="Refunded by" value={sale.refunded_by?.full_name ?? "—"} />
                    {sale.refund_reason ? (
                      <Row label="Reason" value={sale.refund_reason} />
                    ) : null}
                  </>
                ) : null}
              </div>
            </div>
          )}

          <DialogFooter className="sm:justify-between">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPrintOpen(true)}
              disabled={!sale}
            >
              <Printer className="size-4" />
              Print / reprint
            </Button>
            <div className="flex items-center gap-2">
              <Can permission="sales:refund">
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => setRefundOpen(true)}
                  disabled={!refundable}
                >
                  <RotateCcw className="size-4" />
                  Refund
                </Button>
              </Can>
              <Button type="button" variant="ghost" onClick={onClose}>
                Close
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {printOpen ? (
        <InvoicePreviewDialog saleId={saleId} onClose={() => setPrintOpen(false)} />
      ) : null}

      {refundOpen ? (
        <Dialog
          open
          onOpenChange={(next) => !next && !refundMutation.isPending && setRefundOpen(false)}
        >
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Refund this sale?</DialogTitle>
              <DialogDescription>
                Every item goes back into stock, any balance is taken off the customer&apos;s
                account, and the sale is marked refunded. The sale&apos;s figures are kept as
                history; this cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <Field
              label="Reason"
              htmlFor="refund-reason"
              hint="Optional. Recorded on the sale for the audit trail."
            >
              <Input
                id="refund-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="e.g. damaged, customer changed their mind"
                autoComplete="off"
              />
            </Field>
            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setRefundOpen(false)}
                disabled={refundMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => refundMutation.mutate()}
                disabled={refundMutation.isPending}
              >
                {refundMutation.isPending ? "Refunding…" : "Refund sale"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      ) : null}
    </>
  );
}
