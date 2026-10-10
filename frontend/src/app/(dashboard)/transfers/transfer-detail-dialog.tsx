"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Ban, CheckCircle2, Circle, CircleDot, Send, Truck } from "lucide-react";
import { toast } from "sonner";

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
import { Spinner } from "@/components/ui/spinner";
import { describeError } from "@/lib/api/client";
import { transfersApi, type Transfer, type TransferUser } from "@/lib/api/transfers";
import { formatDateTime, formatQuantity } from "@/lib/format";
import {
  availableActions,
  TRANSFER_FLOW,
  TRANSFER_STATUS_META,
  type TransferAction,
} from "@/lib/transfers/status";
import { cn } from "@/lib/utils";

const ACTION_META: Record<TransferAction, { label: string; icon: React.ElementType }> = {
  request: { label: "Submit for approval", icon: Send },
  approve: { label: "Approve", icon: CheckCircle2 },
  ship: { label: "Ship", icon: Truck },
  receive: { label: "Receive", icon: CheckCircle2 },
  cancel: { label: "Cancel transfer", icon: Ban },
};

function statusIndex(status: Transfer["status"]): number {
  return TRANSFER_FLOW.indexOf(status);
}

function Stepper({ status }: { status: Transfer["status"] }) {
  if (status === "cancelled") {
    return (
      <div className="text-destructive bg-destructive/10 flex items-center gap-2 rounded-md px-3 py-2 text-sm">
        <Ban className="size-4" aria-hidden />
        This transfer was cancelled before it shipped. No stock moved.
      </div>
    );
  }
  const current = statusIndex(status);
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-2">
      {TRANSFER_FLOW.map((step, index) => {
        const meta = TRANSFER_STATUS_META[step];
        const done = index < current;
        const active = index === current;
        const Icon = done ? CheckCircle2 : active ? CircleDot : Circle;
        return (
          <li key={step} className="flex items-center gap-2">
            <span
              className={cn(
                "flex items-center gap-1.5 text-sm",
                done && "text-success",
                active && "text-foreground font-medium",
                !done && !active && "text-muted-foreground",
              )}
            >
              <Icon className="size-4" aria-hidden />
              {meta.label}
            </span>
            {index < TRANSFER_FLOW.length - 1 ? (
              <ArrowRight className="text-muted-foreground/50 size-3.5" aria-hidden />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

type HistoryEntry = { label: string; at: string | null; by: TransferUser | null };

function history(transfer: Transfer): HistoryEntry[] {
  return [
    { label: "Created", at: transfer.created_at, by: transfer.created_by },
    { label: "Submitted", at: transfer.requested_at, by: transfer.requested_by },
    { label: "Approved", at: transfer.approved_at, by: transfer.approved_by },
    { label: "Shipped", at: transfer.shipped_at, by: transfer.shipped_by },
    { label: "Received", at: transfer.received_at, by: transfer.received_by },
    { label: "Cancelled", at: transfer.cancelled_at, by: transfer.cancelled_by },
  ].filter((entry) => entry.at !== null);
}

export function TransferDetailDialog({
  transferId,
  onClose,
  onChanged,
}: {
  transferId: string;
  onClose: () => void;
  onChanged?: () => void;
}) {
  const queryClient = useQueryClient();
  const canWrite = useCan("transfers:write");
  const canApprove = useCan("transfers:approve");
  const canShip = useCan("transfers:ship");
  const canReceive = useCan("transfers:receive");

  const [working, setWorking] = React.useState<TransferAction | null>(null);

  const query = useQuery({
    queryKey: ["transfers", transferId],
    queryFn: () => transfersApi.get(transferId),
  });

  async function run(action: TransferAction) {
    setWorking(action);
    try {
      const call = {
        request: () => transfersApi.request(transferId),
        approve: () => transfersApi.approve(transferId),
        ship: () => transfersApi.ship(transferId),
        receive: () => transfersApi.receive(transferId),
        cancel: () => transfersApi.cancel(transferId),
      }[action];
      await call();
      toast.success(`Transfer ${ACTION_META[action].label.toLowerCase()} — done.`);
      await queryClient.invalidateQueries({ queryKey: ["transfers"] });
      onChanged?.();
    } catch (cause) {
      toast.error(describeError(cause));
    } finally {
      setWorking(null);
    }
  }

  const transfer = query.data;
  const meta = transfer ? TRANSFER_STATUS_META[transfer.status] : null;
  const actions = transfer
    ? availableActions(transfer.status, {
        write: canWrite,
        approve: canApprove,
        ship: canShip,
        receive: canReceive,
      })
    : [];
  const busy = working !== null;

  return (
    <Dialog open onOpenChange={(next) => !next && !busy && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex flex-wrap items-center gap-3">
            <span className="font-mono text-base">{transfer?.transfer_number ?? "Transfer"}</span>
            {meta ? <Badge variant={meta.variant}>{meta.label}</Badge> : null}
          </DialogTitle>
          <DialogDescription>{meta?.description}</DialogDescription>
        </DialogHeader>

        {query.isPending ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : query.isError || !transfer || !meta ? (
          <ErrorState
            title="Could not load the transfer"
            description={describeError(query.error)}
            action={
              <Button variant="outline" onClick={() => void query.refetch()}>
                Try again
              </Button>
            }
          />
        ) : (
          <div className="flex flex-col gap-6">
            <Stepper status={transfer.status} />

            <div className="bg-muted/40 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border px-3 py-2 text-sm">
              <span className="font-medium">{transfer.from_branch.name}</span>
              <ArrowRight className="text-muted-foreground size-4" aria-hidden />
              <span className="font-medium">{transfer.to_branch.name}</span>
              {transfer.reference ? (
                <span className="text-muted-foreground">· Ref {transfer.reference}</span>
              ) : null}
            </div>

            {transfer.cancel_reason ? (
              <p className="text-muted-foreground text-sm">
                <span className="text-foreground font-medium">Cancelled: </span>
                {transfer.cancel_reason}
              </p>
            ) : null}

            <section className="flex flex-col gap-2">
              <div className="flex items-baseline justify-between">
                <h3 className="text-sm font-semibold tracking-tight">Items</h3>
                <span className="text-muted-foreground text-xs">
                  {transfer.item_count} line{transfer.item_count === 1 ? "" : "s"} ·{" "}
                  {formatQuantity(transfer.total_quantity)} units
                </span>
              </div>
              <div className="overflow-hidden rounded-md border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-muted-foreground text-xs uppercase">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Product</th>
                      <th className="px-3 py-2 text-left font-medium">SKU</th>
                      <th className="px-3 py-2 text-right font-medium">Quantity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transfer.items.map((line) => (
                      <tr key={line.id} className="border-t">
                        <td className="px-3 py-2">{line.product_name}</td>
                        <td className="text-muted-foreground px-3 py-2 font-mono text-xs">
                          {line.sku}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {formatQuantity(line.quantity)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold tracking-tight">History</h3>
              <ol className="flex flex-col gap-2">
                {history(transfer).map((entry) => (
                  <li key={entry.label} className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium">{entry.label}</span>
                    <span className="text-muted-foreground text-xs">
                      {entry.by?.full_name ?? "System"} · {formatDateTime(entry.at)}
                    </span>
                  </li>
                ))}
              </ol>
            </section>

            {transfer.note ? (
              <p className="text-muted-foreground text-sm">{transfer.note}</p>
            ) : null}

            {actions.length > 0 ? (
              <div className="flex flex-wrap justify-end gap-2 border-t pt-4">
                {actions.map((action) => {
                  const Icon = ACTION_META[action].icon;
                  const isDestructive = action === "cancel";
                  if (action === "ship" || action === "cancel") {
                    return (
                      <ConfirmDialog
                        key={action}
                        title={
                          action === "ship"
                            ? "Ship this transfer?"
                            : "Cancel this transfer?"
                        }
                        description={
                          action === "ship"
                            ? `Stock will leave ${transfer.from_branch.name} now. It arrives at ${transfer.to_branch.name} when received.`
                            : "The transfer is stopped and no stock moves. This cannot be undone."
                        }
                        confirmLabel={ACTION_META[action].label}
                        onConfirm={() => run(action)}
                        trigger={
                          <Button variant={isDestructive ? "outline" : "default"} disabled={busy}>
                            {working === action ? <Spinner /> : <Icon className="size-4" />}
                            {ACTION_META[action].label}
                          </Button>
                        }
                      />
                    );
                  }
                  return (
                    <Button
                      key={action}
                      variant={isDestructive ? "ghost" : "default"}
                      disabled={busy}
                      onClick={() => void run(action)}
                    >
                      {working === action ? <Spinner /> : <Icon className="size-4" />}
                      {ACTION_META[action].label}
                    </Button>
                  );
                })}
              </div>
            ) : null}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
