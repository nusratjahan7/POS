"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, PackageCheck, Trash2, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Can } from "@/components/auth/can";
import { useCan } from "@/components/auth/can";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
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
import { purchasesApi, type Purchase, type PurchaseStatus } from "@/lib/api/purchases";
import { businessApi } from "@/lib/api/settings";
import { formatDateTime, formatMoney, formatQuantity } from "@/lib/format";

const EDITABLE: PurchaseStatus[] = ["draft", "pending"];

const STATUS_BADGE: Record<PurchaseStatus, { label: string; variant: React.ComponentProps<typeof Badge>["variant"] }> = {
  draft: { label: "Draft", variant: "neutral" },
  pending: { label: "Pending", variant: "warning" },
  received: { label: "Received", variant: "success" },
  cancelled: { label: "Cancelled", variant: "outline" },
};

type PurchaseDetailDialogProps = {
  purchaseId: string;
  onClose: () => void;
  onChanged: () => void;
  onEdit: (purchase: Purchase) => void;
};

export function PurchaseDetailDialog({
  purchaseId,
  onClose,
  onChanged,
  onEdit,
}: PurchaseDetailDialogProps) {
  const queryClient = useQueryClient();
  const canReadBusiness = useCan("business:read");

  const detailQuery = useQuery({
    queryKey: ["purchase", purchaseId],
    queryFn: () => purchasesApi.get(purchaseId),
  });
  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canReadBusiness,
  });

  const currency = businessQuery.data?.currency ?? "USD";
  const purchase = detailQuery.data;
  const editable = purchase ? EDITABLE.includes(purchase.status) : false;

  async function receive() {
    if (!purchase) return;
    try {
      await purchasesApi.receive(purchase.id);
      toast.success(`Received ${purchase.purchase_number}`, {
        description: "Stock has been added to the branch.",
      });
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  async function cancel() {
    if (!purchase) return;
    try {
      await purchasesApi.cancel(purchase.id);
      toast.success(`Cancelled ${purchase.purchase_number}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  async function remove() {
    if (!purchase) return;
    try {
      await purchasesApi.remove(purchase.id);
      toast.success(`Deleted ${purchase.purchase_number}`);
      void queryClient.invalidateQueries({ queryKey: ["purchases"] });
      onChanged();
      onClose();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["purchase", purchaseId] });
    void queryClient.invalidateQueries({ queryKey: ["purchases"] });
    void queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    void queryClient.invalidateQueries({ queryKey: ["inventory"] });
    void queryClient.invalidateQueries({ queryKey: ["products"] });
    onChanged();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle>{purchase?.purchase_number ?? "Purchase"}</DialogTitle>
            {purchase ? (
              <Badge variant={STATUS_BADGE[purchase.status].variant}>
                {STATUS_BADGE[purchase.status].label}
              </Badge>
            ) : null}
          </div>
          <DialogDescription>
            {purchase
              ? `Raised ${formatDateTime(purchase.created_at)}${purchase.created_by ? ` by ${purchase.created_by.full_name}` : ""}.`
              : "Loading purchase"}
          </DialogDescription>
        </DialogHeader>

        {detailQuery.isPending ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : detailQuery.error || !purchase ? (
          <ErrorState
            title="Could not load the purchase"
            description={describeError(detailQuery.error)}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 rounded-md border p-3 text-sm sm:grid-cols-4">
              <div className="flex flex-col">
                <span className="text-muted-foreground text-xs">Supplier</span>
                <span className="font-medium">{purchase.supplier.name}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted-foreground text-xs">Branch</span>
                <span className="font-medium">{purchase.branch.name}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted-foreground text-xs">Purchase date</span>
                <span className="font-medium tabular-nums">{purchase.purchase_date}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted-foreground text-xs">Received</span>
                <span className="font-medium tabular-nums">
                  {purchase.received_at ? formatDateTime(purchase.received_at) : "—"}
                </span>
              </div>
            </div>

            <div className="overflow-hidden rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Product</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Unit cost</TableHead>
                    <TableHead className="text-right">Subtotal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {purchase.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="font-medium">{item.product.name}</span>
                          <span className="text-muted-foreground font-mono text-xs">
                            {item.product.sku}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatQuantity(item.quantity)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatMoney(item.unit_price, currency)}
                      </TableCell>
                      <TableCell className="text-right font-medium tabular-nums">
                        {formatMoney(item.subtotal, currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="ml-auto grid w-full max-w-xs grid-cols-2 gap-2 text-sm">
              <span className="text-muted-foreground">Subtotal</span>
              <span className="text-right tabular-nums">{formatMoney(purchase.subtotal, currency)}</span>
              <span className="text-muted-foreground">Discount</span>
              <span className="text-right tabular-nums">{formatMoney(purchase.discount, currency)}</span>
              <span className="text-muted-foreground">Tax</span>
              <span className="text-right tabular-nums">{formatMoney(purchase.tax, currency)}</span>
              <span className="font-medium">Total</span>
              <span className="text-right font-medium tabular-nums">{formatMoney(purchase.total, currency)}</span>
              <span className="text-muted-foreground">Paid</span>
              <span className="text-right tabular-nums">{formatMoney(purchase.paid, currency)}</span>
              <span className="font-medium">Due</span>
              <span className="text-right font-medium tabular-nums">{formatMoney(purchase.due, currency)}</span>
            </div>

            {purchase.note ? (
              <p className="text-muted-foreground text-sm">Note: {purchase.note}</p>
            ) : null}

            <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-4">
              <Can permission="purchases:update">
                {editable ? (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => onEdit(purchase)}>
                      <Pencil className="size-4" />
                      Edit
                    </Button>
                    <ConfirmDialog
                      title={`Cancel ${purchase.purchase_number}?`}
                      description="The purchase is marked cancelled and will not affect stock."
                      confirmLabel="Cancel purchase"
                      onConfirm={cancel}
                      trigger={
                        <Button variant="outline" size="sm">
                          <XCircle className="size-4" />
                          Cancel
                        </Button>
                      }
                    />
                    <ConfirmDialog
                      destructive={false}
                      title={`Receive ${purchase.purchase_number}?`}
                      description="This adds every item to stock in the selected branch, updates the supplier balance and records the payment. This cannot be undone."
                      confirmLabel="Receive purchase"
                      onConfirm={receive}
                      trigger={
                        <Button size="sm">
                          <PackageCheck className="size-4" />
                          Receive
                        </Button>
                      }
                    />
                  </>
                ) : null}
                {purchase.status === "draft" ? (
                  <ConfirmDialog
                    title={`Delete ${purchase.purchase_number}?`}
                    description="A draft purchase is removed permanently."
                    confirmLabel="Delete purchase"
                    onConfirm={remove}
                    trigger={
                      <Button variant="ghost" size="sm">
                        <Trash2 className="size-4" />
                        Delete
                      </Button>
                    }
                  />
                ) : null}
              </Can>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
