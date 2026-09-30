"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Unlock } from "lucide-react";
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
import type { Register } from "@/lib/api/settings";
import { formatMoney } from "@/lib/format";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

type OpenRegisterDialogProps = {
  register: Register;
  currency: string;
  onClose: () => void;
  onOpened: () => void;
};

/** Open a till with its opening float, respecting the register's rules. */
export function OpenRegisterDialog({
  register,
  currency,
  onClose,
  onOpened,
}: OpenRegisterDialogProps) {
  const [opening, setOpening] = React.useState(register.default_opening_balance);
  const [error, setError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      registerSessionsApi.open({
        register_id: register.id,
        opening_cash: opening.trim() === "" ? "0" : opening.trim(),
      }),
    onSuccess: () => {
      toast.success(`${register.name} opened`);
      onOpened();
      onClose();
    },
    onError: (cause) => setFormError(describeError(cause)),
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFormError(null);

    if (!MONEY_PATTERN.test(opening.trim())) {
      setError("Enter an amount like 100 or 100.50.");
      return;
    }
    if (register.require_opening_balance && Number(opening) <= 0) {
      setError("This register requires an opening cash amount greater than zero.");
      return;
    }
    if (
      !register.allow_opening_balance_override &&
      Number(opening) !== Number(register.default_opening_balance)
    ) {
      setError(
        `This register opens with a fixed float of ${formatMoney(
          register.default_opening_balance,
          currency,
        )}.`,
      );
      return;
    }
    mutation.mutate();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !mutation.isPending && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Unlock className="size-4" aria-hidden />
            Open {register.name}
          </DialogTitle>
          <DialogDescription>
            Count the float in the drawer and record it. Sales can only be rung once the register is
            open.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not open the register</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <Field
            label="Opening cash"
            htmlFor="opening-cash"
            error={error}
            hint={
              register.allow_opening_balance_override
                ? `Suggested float: ${formatMoney(register.default_opening_balance, currency)}`
                : `Fixed float: ${formatMoney(register.default_opening_balance, currency)}`
            }
          >
            <Input
              id="opening-cash"
              inputMode="decimal"
              value={opening}
              onChange={(event) => setOpening(event.target.value)}
              placeholder="0.00"
              autoComplete="off"
            />
          </Field>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? <Spinner /> : null}
              Open register
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
