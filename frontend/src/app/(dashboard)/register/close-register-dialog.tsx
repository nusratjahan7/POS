"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { describeError } from "@/lib/api/client";
import { registerSessionsApi, type RegisterSessionDetail } from "@/lib/api/register-sessions";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

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

type CloseRegisterDialogProps = {
  detail: RegisterSessionDetail;
  currency: string;
  onClose: () => void;
  onClosed: () => void;
};

/** Reconcile and close: the drawer's expected figure against what was counted. */
export function CloseRegisterDialog({
  detail,
  currency,
  onClose,
  onClosed,
}: CloseRegisterDialogProps) {
  const [actual, setActual] = React.useState("");
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);

  const { session, summary } = detail;
  const expected = Number(summary.expected_cash);
  const counted = MONEY_PATTERN.test(actual.trim()) ? Number(actual) : null;
  const difference = counted === null ? null : counted - expected;
  const money = (value: string | number) => formatMoney(value, currency);

  const mutation = useMutation({
    mutationFn: () =>
      registerSessionsApi.close(session.id, {
        actual_cash: actual.trim(),
        note: note.trim() || null,
      }),
    onSuccess: () => {
      toast.success(`${session.register.name} closed`);
      onClosed();
      onClose();
    },
    onError: (cause) => setFormError(describeError(cause)),
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFormError(null);
    if (!MONEY_PATTERN.test(actual.trim())) {
      setError("Count the drawer and enter the amount like 100 or 100.50.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !mutation.isPending && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="size-4" aria-hidden />
            Close {session.register.name}
          </DialogTitle>
          <DialogDescription>
            This is the drawer&apos;s reconciliation. Count the cash, enter it, and the difference is
            recorded.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not close the register</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="flex flex-col gap-1.5 rounded-md border p-3 text-sm">
            <Row label="Opening cash" value={money(summary.opening_cash)} />
            <Row label="Cash sales" value={money(summary.cash_sales)} />
            <Row label="Cash refunds" value={`− ${money(summary.cash_refunds)}`} />
            <Row label="Cash expenses" value={`− ${money(summary.cash_expenses)}`} />
            <Row label="Cash in" value={money(summary.cash_in)} />
            <Row label="Cash out" value={`− ${money(summary.cash_out)}`} />
            <Row label="Expected in the drawer" value={money(summary.expected_cash)} strong />
          </div>

          <Field label="Counted (actual) cash" htmlFor="actual-cash" error={error}>
            <Input
              id="actual-cash"
              inputMode="decimal"
              value={actual}
              onChange={(event) => setActual(event.target.value)}
              placeholder="0.00"
              autoComplete="off"
            />
          </Field>

          {difference !== null ? (
            <div
              className={cn(
                "flex items-center justify-between rounded-md border p-3 text-sm font-medium",
                difference === 0
                  ? "text-success"
                  : difference < 0
                    ? "text-destructive"
                    : "text-warning-foreground",
              )}
            >
              <span>{difference === 0 ? "Balanced" : difference < 0 ? "Short" : "Over"}</span>
              <span className="tabular-nums">{money(Math.abs(difference))}</span>
            </div>
          ) : null}

          <Field label="Note" htmlFor="closing-note" hint="Optional — e.g. why the drawer is off.">
            <Input
              id="closing-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              autoComplete="off"
            />
          </Field>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? <Spinner /> : null}
              Close register
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
