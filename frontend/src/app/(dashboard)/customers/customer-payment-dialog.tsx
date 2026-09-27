"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { describeError } from "@/lib/api/client";
import { customersApi, type Customer } from "@/lib/api/customers";
import { businessApi, paymentMethodsApi } from "@/lib/api/settings";
import { formatMoney } from "@/lib/format";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

type CustomerPaymentDialogProps = {
  customer: Customer;
  onClose: () => void;
  onPaid: () => void;
};

export function CustomerPaymentDialog({ customer, onClose, onPaid }: CustomerPaymentDialogProps) {
  const [amount, setAmount] = React.useState("");
  const [method, setMethod] = React.useState<string>("");
  const [reference, setReference] = React.useState("");
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  const methodsQuery = useQuery({
    queryKey: ["payment-methods", "options"],
    queryFn: () => paymentMethodsApi.options(),
  });
  const businessQuery = useQuery({ queryKey: ["business"], queryFn: () => businessApi.get() });

  const currency = businessQuery.data?.currency ?? "USD";
  const methods = methodsQuery.data ?? [];
  const due = Number(customer.balance);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFormError(null);

    if (!MONEY_PATTERN.test(amount) || Number(amount) <= 0) {
      setError("Enter an amount like 100 or 100.50.");
      return;
    }
    if (Number(amount) > due) {
      setError("The payment cannot exceed the outstanding due.");
      return;
    }

    setSaving(true);
    try {
      await customersApi.recordPayment(customer.id, {
        amount,
        method: method || null,
        reference: reference.trim() || null,
        note: note.trim() || null,
      });
      toast.success("Payment recorded", { description: `${customer.name}'s balance updated.` });
      onPaid();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !saving && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Record a payment</DialogTitle>
          <DialogDescription>
            {customer.name} owes {formatMoney(customer.balance, currency)}.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not record the payment</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Amount" htmlFor="payment-amount" error={error}>
              <Input
                id="payment-amount"
                inputMode="decimal"
                placeholder="0.00"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                autoComplete="off"
              />
            </Field>

            <Field label="Method" htmlFor="payment-method">
              <Select value={method} onValueChange={setMethod}>
                <SelectTrigger id="payment-method" className="w-full">
                  <SelectValue placeholder="Optional" />
                </SelectTrigger>
                <SelectContent>
                  {methods.map((option) => (
                    <SelectItem key={option.id} value={option.code}>
                      {option.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Reference" htmlFor="payment-reference" className="sm:col-span-2">
              <Input
                id="payment-reference"
                placeholder="Optional — e.g. transaction id"
                value={reference}
                onChange={(event) => setReference(event.target.value)}
                autoComplete="off"
              />
            </Field>

            <Field label="Note" htmlFor="payment-note" className="sm:col-span-2">
              <Input
                id="payment-note"
                placeholder="Optional"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                autoComplete="off"
              />
            </Field>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || due <= 0}>
              {saving ? <Spinner /> : null}
              Record payment
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
