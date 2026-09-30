"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Printer, RotateCcw } from "lucide-react";

import { SaleReturnDialog } from "@/app/(dashboard)/sales/sale-return-dialog";
import { Can } from "@/components/auth/can";
import { InvoicePreviewDialog } from "@/components/invoice/invoice-preview-dialog";
import {
  PaymentStatusBadge,
  ReturnStatusBadge,
  SaleStatusBadge,
} from "@/components/sales/status-badge";
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
import { formatAmount, formatDateTime, formatQuantity } from "@/lib/format";

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
 * One sale in full: its invoice details, lines, tenders, totals, return history
 * and timestamps, with the receipt actions (print / reprint) and the return flow.
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
  const [returnOpen, setReturnOpen] = React.useState(false);

  const receiptQuery = useQuery({
    queryKey: ["sale-receipt", saleId],
    queryFn: () => salesApi.receipt(saleId),
  });
  const returnsQuery = useQuery({
    queryKey: ["sale-returns", saleId],
    queryFn: () => salesApi.listReturns(saleId),
  });

  const receipt = receiptQuery.data;
  const sale = receipt?.sale;
  const money = (value: string | number | null | undefined) => formatAmount(value);
  const returns = returnsQuery.data ?? [];

  function handleReturned() {
    void queryClient.invalidateQueries({ queryKey: ["sale-receipt", saleId] });
    void queryClient.invalidateQueries({ queryKey: ["sale-returns", saleId] });
    onChanged();
  }

  const returnable = sale?.status === "completed";

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
              {receipt ? `${receipt.business.name} · ${receipt.branch.name}` : "Loading the sale…"}
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
                {/* What the customer handed over, not the amount applied. */}
                <Row label="Paid" value={money(sale.received_amount)} />
                {Number(sale.change_amount) > 0 ? (
                  <Row label="Change" value={money(sale.change_amount)} />
                ) : null}
                {Number(sale.due) > 0 ? <Row label="Due" value={money(sale.due)} strong /> : null}
                {Number(sale.returned_amount) > 0 ? (
                  <Row label="Returned" value={`-${money(sale.returned_amount)}`} />
                ) : null}
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

              <div className="flex flex-col gap-2">
                <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                  Returns
                </h3>
                {returnsQuery.isPending ? (
                  <Skeleton className="h-16 w-full" />
                ) : returns.length === 0 ? (
                  <p className="text-muted-foreground rounded-md border p-3 text-sm">
                    Nothing has been returned from this sale.
                  </p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {returns.map((record) => (
                      <div key={record.id} className="flex flex-col gap-2 rounded-md border p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-xs font-medium">
                              {record.return_number}
                            </span>
                            <ReturnStatusBadge status={record.status} />
                          </div>
                          <span className="font-medium tabular-nums">
                            {money(record.refund_amount)}
                          </span>
                        </div>
                        <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 text-xs">
                          <span>{formatDateTime(record.completed_at ?? record.created_at)}</span>
                          <span>
                            {Number(record.cash_refund) > 0
                              ? `${money(record.cash_refund)} paid out`
                              : "settled against balance"}
                          </span>
                          {record.payment_method ? <span>{record.payment_method.name}</span> : null}
                          {record.created_by ? <span>by {record.created_by.full_name}</span> : null}
                        </div>
                        {record.reason ? <p className="text-sm">{record.reason}</p> : null}
                        <ul className="text-muted-foreground text-xs">
                          {record.items.map((item) => (
                            <li key={item.id}>
                              {item.product_name} × {formatQuantity(item.quantity)} —{" "}
                              {money(item.line_total)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-1 rounded-md border p-3">
                <Row label="Sold" value={formatDateTime(sale.sold_at)} />
                <Row label="Created" value={formatDateTime(sale.created_at)} />
                {sale.refunded_at ? (
                  <>
                    <Row label="Refunded" value={formatDateTime(sale.refunded_at)} />
                    <Row label="Refunded by" value={sale.refunded_by?.full_name ?? "—"} />
                    {sale.refund_reason ? <Row label="Reason" value={sale.refund_reason} /> : null}
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
                  variant="secondary"
                  onClick={() => setReturnOpen(true)}
                  disabled={!returnable}
                >
                  <RotateCcw className="size-4" />
                  Return
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

      {returnOpen && sale ? (
        <SaleReturnDialog
          sale={sale}
          onClose={() => setReturnOpen(false)}
          onReturned={handleReturned}
        />
      ) : null}
    </>
  );
}
