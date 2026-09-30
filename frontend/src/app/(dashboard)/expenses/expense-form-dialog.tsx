"use client";

import * as React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
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
import { expenseCategoriesApi, expensesApi } from "@/lib/api/expenses";
import { registerSessionsApi } from "@/lib/api/register-sessions";
import { branchesApi } from "@/lib/api/rbac";
import { paymentMethodsApi } from "@/lib/api/settings";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

type ExpenseFormDialogProps = {
  onClose: () => void;
  onSaved: () => void;
};

/** Record a spend, filing it by category and settling it from a method/drawer. */
export function ExpenseFormDialog({ onClose, onSaved }: ExpenseFormDialogProps) {
  const [amount, setAmount] = React.useState("");
  const [categoryId, setCategoryId] = React.useState("");
  const [methodId, setMethodId] = React.useState("");
  const [branchId, setBranchId] = React.useState("");
  const [spentAt, setSpentAt] = React.useState(today());
  const [description, setDescription] = React.useState("");
  const [reference, setReference] = React.useState("");
  const [sessionId, setSessionId] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const branchesQuery = useQuery({ queryKey: ["branches", "options"], queryFn: branchesApi.options });
  const categoriesQuery = useQuery({
    queryKey: ["expense-categories", "options"],
    queryFn: expenseCategoriesApi.options,
  });
  const methodsQuery = useQuery({
    queryKey: ["payment-methods", "options"],
    queryFn: paymentMethodsApi.options,
  });
  const openSessionsQuery = useQuery({
    queryKey: ["register-sessions", "open", branchId],
    queryFn: () => registerSessionsApi.openSessions(branchId || undefined),
    enabled: Boolean(branchId),
  });

  const branches = branchesQuery.data ?? [];
  const categories = categoriesQuery.data ?? [];
  const methods = methodsQuery.data ?? [];
  const sessions = openSessionsQuery.data ?? [];
  const method = methods.find((row) => row.id === methodId);
  const isCash = Boolean(method?.opens_cash_drawer);

  // Default the branch and category to the first option, derived rather than
  // stored so no effect is needed to keep them in step.
  const effectiveBranch = branchId || branches[0]?.id || "";
  const effectiveCategory = categoryId || categories[0]?.id || "";

  const mutation = useMutation({
    mutationFn: () =>
      expensesApi.create({
        branch_id: effectiveBranch,
        category_id: effectiveCategory,
        payment_method_id: methodId,
        amount: amount.trim(),
        description: description.trim() || null,
        reference: reference.trim() || null,
        spent_at: spentAt,
        register_session_id: isCash ? sessionId || null : null,
      }),
    onSuccess: () => {
      toast.success("Expense recorded");
      onSaved();
      onClose();
    },
    onError: (cause) => setError(describeError(cause)),
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!MONEY_PATTERN.test(amount.trim()) || Number(amount) <= 0) {
      setError("Enter an amount like 100 or 100.50.");
      return;
    }
    if (!effectiveCategory || !methodId || !effectiveBranch) {
      setError("Choose a branch, a category and a payment method.");
      return;
    }
    if (isCash && !sessionId) {
      setError("A cash expense needs the open register it is paid from.");
      return;
    }
    mutation.mutate();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !mutation.isPending && onClose()}>
      <DialogContent className="max-h-[85svh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Record an expense</DialogTitle>
          <DialogDescription>
            A cash expense is taken from an open register&apos;s drawer.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {error ? (
            <Alert variant="destructive">
              <AlertTitle>Could not record the expense</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Amount" htmlFor="expense-amount">
              <Input
                id="expense-amount"
                inputMode="decimal"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0.00"
                autoComplete="off"
              />
            </Field>

            <Field label="Date" htmlFor="expense-date">
              <Input
                id="expense-date"
                type="date"
                value={spentAt}
                onChange={(event) => setSpentAt(event.target.value)}
              />
            </Field>

            <Field label="Category" htmlFor="expense-category">
              <Select value={effectiveCategory} onValueChange={setCategoryId}>
                <SelectTrigger id="expense-category" className="w-full">
                  <SelectValue placeholder="Choose" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((option) => (
                    <SelectItem key={option.id} value={option.id}>
                      {option.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Payment method" htmlFor="expense-method">
              <Select value={methodId} onValueChange={setMethodId}>
                <SelectTrigger id="expense-method" className="w-full">
                  <SelectValue placeholder="Choose" />
                </SelectTrigger>
                <SelectContent>
                  {methods.map((option) => (
                    <SelectItem key={option.id} value={option.id}>
                      {option.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Branch" htmlFor="expense-branch">
              <Select
                value={effectiveBranch}
                onValueChange={(value) => {
                  setBranchId(value);
                  setSessionId("");
                }}
              >
                <SelectTrigger id="expense-branch" className="w-full">
                  <SelectValue placeholder="Choose" />
                </SelectTrigger>
                <SelectContent>
                  {branches.map((option) => (
                    <SelectItem key={option.id} value={option.id}>
                      {option.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            {isCash ? (
              <Field
                label="Paid from register"
                htmlFor="expense-session"
                hint={sessions.length === 0 ? "No register is open at this branch." : undefined}
              >
                <Select value={sessionId} onValueChange={setSessionId}>
                  <SelectTrigger id="expense-session" className="w-full">
                    <SelectValue placeholder="Open register" />
                  </SelectTrigger>
                  <SelectContent>
                    {sessions.map((session) => (
                      <SelectItem key={session.id} value={session.id}>
                        {session.register.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            ) : null}

            <Field label="Description" htmlFor="expense-description" className="sm:col-span-2">
              <Input
                id="expense-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Optional"
                autoComplete="off"
              />
            </Field>

            <Field label="Reference" htmlFor="expense-reference" className="sm:col-span-2">
              <Input
                id="expense-reference"
                value={reference}
                onChange={(event) => setReference(event.target.value)}
                placeholder="Optional — e.g. receipt number"
                autoComplete="off"
              />
            </Field>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? <Spinner /> : null}
              Record expense
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
