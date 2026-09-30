"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowDownCircle, ArrowUpCircle } from "lucide-react";
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
import { registerSessionsApi } from "@/lib/api/register-sessions";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

type CashMovementDialogProps = {
  sessionId: string;
  direction: "in" | "out";
  onClose: () => void;
  onDone: () => void;
};

/** Put cash into, or take cash out of, the drawer mid-shift. */
export function CashMovementDialog({
  sessionId,
  direction,
  onClose,
  onDone,
}: CashMovementDialogProps) {
  const [amount, setAmount] = React.useState("");
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);

  const isIn = direction === "in";
  const verb = isIn ? "Cash in" : "Cash out";

  const mutation = useMutation({
    mutationFn: () =>
      (isIn ? registerSessionsApi.cashIn : registerSessionsApi.cashOut)(sessionId, {
        amount: amount.trim(),
        note: note.trim() || null,
      }),
    onSuccess: () => {
      toast.success(`${verb} recorded`);
      onDone();
      onClose();
    },
    onError: (cause) => setFormError(describeError(cause)),
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFormError(null);
    if (!MONEY_PATTERN.test(amount.trim()) || Number(amount) <= 0) {
      setError("Enter an amount like 100 or 100.50.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !mutation.isPending && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {isIn ? (
              <ArrowDownCircle className="size-4" aria-hidden />
            ) : (
              <ArrowUpCircle className="size-4" aria-hidden />
            )}
            {verb}
          </DialogTitle>
          <DialogDescription>
            {isIn
              ? "Add cash to the drawer — e.g. a float top-up. It raises the expected cash."
              : "Take cash from the drawer — e.g. a petty purchase. It lowers the expected cash."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not record it</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <Field label="Amount" htmlFor="cash-amount" error={error}>
            <Input
              id="cash-amount"
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="0.00"
              autoComplete="off"
            />
          </Field>

          <Field label="Reason" htmlFor="cash-note" hint="Optional.">
            <Input
              id="cash-note"
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
              {verb}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
