"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, ShoppingBag } from "lucide-react";

import { CustomerPaymentDialog } from "@/app/(dashboard)/customers/customer-payment-dialog";
import { Can } from "@/components/auth/can";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
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
import { customersApi } from "@/lib/api/customers";
import { businessApi } from "@/lib/api/settings";
import { formatDateTime, formatMoney } from "@/lib/format";

type CustomerDetailsDialogProps = {
  customerId: string;
  onClose: () => void;
  onChanged: () => void;
};

export function CustomerDetailsDialog({
  customerId,
  onClose,
  onChanged,
}: CustomerDetailsDialogProps) {
  const queryClient = useQueryClient();
  const [paymentOpen, setPaymentOpen] = React.useState(false);

  const detailsQuery = useQuery({
    queryKey: ["customer", customerId, "details"],
    queryFn: () => customersApi.details(customerId),
  });
  const businessQuery = useQuery({ queryKey: ["business"], queryFn: () => businessApi.get() });

  const currency = businessQuery.data?.currency ?? "USD";
  const details = detailsQuery.data;

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["customer", customerId] });
    void queryClient.invalidateQueries({ queryKey: ["customers"] });
    onChanged();
  }

  const stats = details
    ? [
        { label: "Total orders", value: String(details.total_orders) },
        { label: "Purchase amount", value: formatMoney(details.total_purchase_amount, currency) },
        { label: "Total paid", value: formatMoney(details.total_paid, currency) },
        { label: "Outstanding due", value: formatMoney(details.outstanding_due, currency) },
      ]
    : [];

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle>{details?.customer.name ?? "Customer"}</DialogTitle>
            {details ? (
              <Badge variant={details.customer.is_active ? "success" : "outline"}>
                {details.customer.is_active ? "Active" : "Inactive"}
              </Badge>
            ) : null}
          </div>
          <DialogDescription>
            Account statement: totals, payments and purchase history.
          </DialogDescription>
        </DialogHeader>

        {detailsQuery.isPending ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : detailsQuery.error || !details ? (
          <ErrorState
            title="Could not load the customer"
            description={describeError(detailsQuery.error)}
          />
        ) : (
          <div className="flex flex-col gap-5">
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <div className="flex flex-col">
                <span className="text-muted-foreground text-xs">Phone</span>
                <span>{details.customer.phone ?? "—"}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted-foreground text-xs">Email</span>
                <span className="truncate">{details.customer.email ?? "—"}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted-foreground text-xs">Address</span>
                <span className="truncate">{details.customer.address ?? "—"}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="rounded-lg border p-3">
                  <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                    {stat.label}
                  </div>
                  <div className="mt-1 text-lg font-semibold tabular-nums">{stat.value}</div>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold">Payment history</h3>
                <Can permission="customers:write">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPaymentOpen(true)}
                    disabled={Number(details.outstanding_due) <= 0}
                  >
                    <Plus className="size-4" />
                    Record payment
                  </Button>
                </Can>
              </div>

              {details.recent_payments.length === 0 ? (
                <EmptyState
                  size="compact"
                  title="No payments yet"
                  description="Payments received against this account will appear here."
                />
              ) : (
                <div className="overflow-hidden rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Method</TableHead>
                        <TableHead>By</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {details.recent_payments.map((payment) => (
                        <TableRow key={payment.id}>
                          <TableCell className="text-muted-foreground text-sm tabular-nums">
                            {formatDateTime(payment.paid_at)}
                          </TableCell>
                          <TableCell className="text-sm">{payment.method ?? "—"}</TableCell>
                          <TableCell className="text-sm">
                            {payment.user?.full_name ?? "System"}
                          </TableCell>
                          <TableCell className="text-right font-medium tabular-nums">
                            {formatMoney(payment.amount, currency)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3">
              <h3 className="text-sm font-semibold">Purchase history</h3>
              {details.recent_purchases.length === 0 ? (
                <EmptyState
                  icon={ShoppingBag}
                  size="compact"
                  title="No purchases yet"
                  description="Sales made to this customer will appear here."
                />
              ) : (
                <div className="overflow-hidden rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Reference</TableHead>
                        <TableHead className="text-right">Total</TableHead>
                        <TableHead className="text-right">Paid</TableHead>
                        <TableHead className="text-right">Due</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {details.recent_purchases.map((purchase) => (
                        <TableRow key={purchase.id}>
                          <TableCell className="text-muted-foreground text-sm tabular-nums">
                            {formatDateTime(purchase.purchased_at)}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {purchase.reference}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatMoney(purchase.total, currency)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatMoney(purchase.paid, currency)}
                          </TableCell>
                          <TableCell className="text-right font-medium tabular-nums">
                            {formatMoney(purchase.due, currency)}
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

      {paymentOpen && details ? (
        <CustomerPaymentDialog
          customer={details.customer}
          onClose={() => setPaymentOpen(false)}
          onPaid={refresh}
        />
      ) : null}
    </Dialog>
  );
}
