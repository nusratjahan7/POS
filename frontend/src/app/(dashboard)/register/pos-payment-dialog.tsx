"use client";

import * as React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, FileText, Plus, Receipt, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { InvoicePreviewDialog } from "@/components/invoice/invoice-preview-dialog";
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
import { describeError } from "@/lib/api/client";
import { discountsApi } from "@/lib/api/discounts";
import { salesApi, type Sale } from "@/lib/api/sales";
import { paymentMethodsApi, type PaymentMethodOption } from "@/lib/api/settings";
import type { CartLine, CartTotals, PosCustomer } from "@/lib/pos/cart-store";
import type { InvoiceVariant } from "@/lib/invoice/styles";
import { formatMoney, formatQuantity } from "@/lib/format";

/** One tender line: which method, how much of the sale it settles, and its detail. */
type Tender = {
  key: string;
  methodId: string;
  amount: string;
  received: string;
  reference: string;
};

let tenderSeq = 0;

function nextTenderKey(): string {
  tenderSeq += 1;
  return `tender-${tenderSeq}`;
}

const money = (value: number, currency: string) => formatMoney(value, currency);

export function PosPaymentDialog({
  lines,
  totals,
  orderDiscount,
  customer,
  branchId,
  registerId,
  couponCode,
  onCouponChange,
  currency,
  onClose,
  onComplete,
}: {
  lines: readonly CartLine[];
  totals: CartTotals;
  orderDiscount: number;
  customer: PosCustomer | null;
  branchId: string;
  registerId: string;
  couponCode: string;
  onCouponChange: (code: string) => void;
  currency: string;
  onClose: () => void;
  onComplete: (sale: Sale) => void;
}) {
  const methodsQuery = useQuery({
    queryKey: ["payment-methods", "options"],
    queryFn: () => paymentMethodsApi.options(),
  });
  const methods = React.useMemo(() => methodsQuery.data ?? [], [methodsQuery.data]);

  const [tenders, setTenders] = React.useState<Tender[]>([]);
  const [note, setNote] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [completed, setCompleted] = React.useState<Sale | null>(null);
  // Which invoice layout to preview once the sale is done; null keeps it closed.
  const [invoiceVariant, setInvoiceVariant] = React.useState<InvoiceVariant | null>(null);

  const methodById = React.useMemo(() => {
    const map = new Map<string, PaymentMethodOption>();
    for (const method of methods) map.set(method.id, method);
    return map;
  }, [methods]);

  // The server prices the discounts — the till only shows what it says. This is
  // a preview; creating the sale recomputes everything authoritative.
  const previewQuery = useQuery({
    queryKey: [
      "discount-preview",
      couponCode,
      customer?.id ?? null,
      orderDiscount,
      lines.map((line) => [line.productId, line.quantity, line.discount]),
    ],
    queryFn: () =>
      discountsApi.validate({
        customer_id: customer?.id ?? null,
        coupon_code: couponCode || null,
        order_discount: orderDiscount.toFixed(2),
        items: lines.map((line) => ({
          product_id: line.productId,
          quantity: String(line.quantity),
          discount: line.discount.toFixed(2),
        })),
      }),
    enabled: lines.length > 0,
    retry: false,
  });

  // What the customer actually owes. The server prices the basket — promotions,
  // the coupon and tax — so its total is authoritative; the cart's own total is
  // only an estimate until the preview answers.
  const payable = previewQuery.data ? Number(previewQuery.data.total) : totals.total;

  // Before the cashier touches anything, the whole total sits on the default
  // method. Derived rather than stored, so it follows the total and needs no
  // effect to keep in step.
  const defaultTender = React.useMemo<Tender | null>(() => {
    if (methods.length === 0) return null;
    const preferred = methods.find((method) => method.kind === "cash") ?? methods[0];
    return {
      key: "default",
      methodId: preferred.id,
      amount: payable.toFixed(2),
      received: payable.toFixed(2),
      reference: "",
    };
  }, [methods, payable]);

  const shown = tenders.length > 0 ? tenders : defaultTender ? [defaultTender] : [];

  // What each tender actually applies to the sale. A cash tender applies only
  // what is still due and treats the rest of what was handed over as change, so
  // the applied total can never exceed the amount due. Non-cash methods apply
  // exactly what was entered — only cash can give change, so an over-application
  // on a card is reported rather than silently absorbed.
  let remaining = payable;
  const appliedByTender: number[] = [];
  for (const tender of shown) {
    const cash = methodById.get(tender.methodId)?.kind === "cash";
    const entered = cash ? Number(tender.received) || 0 : Number(tender.amount) || 0;
    const apply = cash
      ? Math.min(Math.max(entered, 0), Math.max(remaining, 0))
      : Math.max(entered, 0);
    appliedByTender.push(apply);
    remaining = Math.max(remaining - apply, 0);
  }

  const applied = appliedByTender.reduce((sum, value) => sum + value, 0);
  const overpaid = Math.max(applied - payable, 0);
  const change = shown.reduce((sum, tender, index) => {
    if (methodById.get(tender.methodId)?.kind !== "cash") return sum;
    return sum + Math.max((Number(tender.received) || 0) - appliedByTender[index], 0);
  }, 0);
  const due = Math.max(payable - applied, 0);

  const missingReference = shown.find((tender) => {
    const method = methodById.get(tender.methodId);
    return Boolean(method?.requires_reference) && !tender.reference.trim();
  });

  const blocking =
    shown.length === 0 || applied <= 0
      ? "Enter how the customer is paying."
      : overpaid > 0
        ? `${money(overpaid, currency)} beyond the total is applied on a non-cash method. Only cash gives change — reduce it.`
        : due > 0 && !customer
          ? `${money(due, currency)} would be left unpaid. Choose a customer to carry it, or take the full amount.`
          : missingReference
            ? `${methodById.get(missingReference.methodId)?.name ?? "That method"} needs a reference.`
            : null;

  function updateTender(key: string, patch: Partial<Tender>) {
    setTenders(
      shown.map((tender) => (tender.key === key ? { ...tender, ...patch } : tender)),
    );
  }

  function changeMethod(key: string, methodId: string) {
    const isCash = methodById.get(methodId)?.kind === "cash";
    setTenders(
      shown.map((tender) =>
        tender.key === key
          ? {
              ...tender,
              methodId,
              // A cash row is driven by what was received; seed it so the field
              // is never blank when there is an amount to apply.
              received: isCash && !tender.received ? tender.amount : tender.received,
            }
          : tender,
      ),
    );
  }

  function addTender() {
    const fallback =
      methods.find((method) => method.kind === "card") ?? methods[1] ?? methods[0];
    if (!fallback) return;
    const key = nextTenderKey();
    const amount = (due > 0 ? due : 0).toFixed(2);
    setTenders([
      ...shown,
      {
        key,
        methodId: fallback.id,
        amount,
        received: fallback.kind === "cash" ? amount : "",
        reference: "",
      },
    ]);
  }

  const mutation = useMutation({
    mutationFn: () =>
      salesApi.create({
        branch_id: branchId,
        register_id: registerId,
        customer_id: customer?.id ?? null,
        coupon_code: couponCode || null,
        note: note.trim() || null,
        order_discount: orderDiscount.toFixed(2),
        items: lines.map((line) => ({
          product_id: line.productId,
          quantity: String(line.quantity),
          discount: line.discount.toFixed(2),
        })),
        payments: shown.map((tender, index) => {
          const method = methodById.get(tender.methodId);
          const amount = appliedByTender[index];
          const received = Number(tender.received) || 0;
          return {
            payment_method_id: tender.methodId,
            amount: amount.toFixed(2),
            // Only cash can give change, and only when more was handed over.
            tendered:
              method?.kind === "cash" && received > amount ? received.toFixed(2) : null,
            reference: tender.reference.trim() || null,
          };
        }),
      }),
    onSuccess: (sale) => {
      setCompleted(sale);
      onComplete(sale);
    },
    onError: (cause: unknown) => {
      const message = describeError(cause);
      setError(message);
      toast.error(message);
    },
  });

  // --- Success: the sale is committed, the invoice number stays on screen -----
  if (completed) {
    return (
      <>
        <Dialog open onOpenChange={(next) => !next && onClose()}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CheckCircle2 className="text-success size-5" aria-hidden />
                Payment complete
              </DialogTitle>
              <DialogDescription>
                Hand back any change, then start the next sale.
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-col gap-2 rounded-md border p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground text-sm">Invoice</span>
                <span className="font-mono text-sm font-semibold">{completed.sale_number}</span>
              </div>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="text-muted-foreground">Items</span>
                <span className="tabular-nums">
                  {formatQuantity(
                    completed.items.reduce((sum, item) => sum + Number(item.quantity), 0),
                  )}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="text-muted-foreground">Total</span>
                <span className="tabular-nums">{money(Number(completed.total), currency)}</span>
              </div>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="text-muted-foreground">Paid</span>
                <span className="tabular-nums">{money(Number(completed.paid), currency)}</span>
              </div>
              {Number(completed.change_amount) > 0 ? (
                <div className="flex items-center justify-between gap-3 border-t pt-2 text-base font-semibold">
                  <span>Change</span>
                  <span className="tabular-nums">
                    {money(Number(completed.change_amount), currency)}
                  </span>
                </div>
              ) : null}
              {Number(completed.due) > 0 ? (
                <div className="text-warning flex items-start gap-2 border-t pt-2 text-sm">
                  <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                  <span>
                    {money(Number(completed.due), currency)} is on{" "}
                    {completed.customer?.name ?? "the customer"}&apos;s account.
                  </span>
                </div>
              ) : null}
            </div>

            <DialogFooter className="sm:justify-between">
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setInvoiceVariant("thermal")}
                >
                  <Receipt className="size-4" />
                  Thermal receipt
                </Button>
                <Button type="button" variant="outline" onClick={() => setInvoiceVariant("a4")}>
                  <FileText className="size-4" />
                  A4 invoice
                </Button>
              </div>
              <Button type="button" onClick={onClose}>
                New sale
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {invoiceVariant ? (
          <InvoicePreviewDialog
            saleId={completed.id}
            defaultVariant={invoiceVariant}
            onClose={() => setInvoiceVariant(null)}
          />
        ) : null}
      </>
    );
  }

  // --- Payment ---------------------------------------------------------------
  return (
    <Dialog open onOpenChange={(next) => !next && !mutation.isPending && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Take payment</DialogTitle>
          <DialogDescription>
            {customer ? `On ${customer.name}'s sale.` : "Walk-in sale."} The server calculates the
            final figures.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-end justify-between gap-3 rounded-md border p-3">
          <span className="text-muted-foreground text-sm">Amount due</span>
          <span className="text-2xl leading-none font-semibold tabular-nums">
            {money(payable, currency)}
          </span>
        </div>

        {methodsQuery.isPending ? (
          <p className="text-muted-foreground text-sm">Loading payment methods…</p>
        ) : (
          <div className="flex flex-col gap-3">
            {shown.map((tender, index) => {
              const method = methodById.get(tender.methodId);
              return (
                <div key={tender.key} className="flex flex-col gap-2 rounded-md border p-3">
                  <div className="flex items-center gap-2">
                    <Select
                      value={tender.methodId}
                      onValueChange={(value) => changeMethod(tender.key, value)}
                    >
                      <SelectTrigger className="flex-1" aria-label={`Payment method ${index + 1}`}>
                        <SelectValue placeholder="Method" />
                      </SelectTrigger>
                      <SelectContent>
                        {methods.map((option) => (
                          <SelectItem key={option.id} value={option.id}>
                            {option.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {shown.length > 1 ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label="Remove this payment"
                        onClick={() => setTenders(shown.filter((row) => row.key !== tender.key))}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    ) : null}
                  </div>

                  {method?.kind === "cash" ? (
                    <Field
                      label="Amount received"
                      htmlFor={`received-${tender.key}`}
                      hint="Change is worked out for you."
                    >
                      <Input
                        id={`received-${tender.key}`}
                        inputMode="decimal"
                        value={tender.received}
                        onChange={(event) =>
                          updateTender(tender.key, { received: event.target.value })
                        }
                        placeholder="0.00"
                        className="tabular-nums"
                      />
                    </Field>
                  ) : (
                    <Field label="Amount" htmlFor={`amount-${tender.key}`}>
                      <Input
                        id={`amount-${tender.key}`}
                        inputMode="decimal"
                        value={tender.amount}
                        onChange={(event) =>
                          updateTender(tender.key, { amount: event.target.value })
                        }
                        placeholder="0.00"
                        className="tabular-nums"
                      />
                    </Field>
                  )}

                  {method?.requires_reference ? (
                    <Field
                      label="Reference"
                      htmlFor={`reference-${tender.key}`}
                      hint={`${method.name} needs its transaction reference.`}
                    >
                      <Input
                        id={`reference-${tender.key}`}
                        value={tender.reference}
                        onChange={(event) =>
                          updateTender(tender.key, { reference: event.target.value })
                        }
                        placeholder="e.g. approval code"
                        autoComplete="off"
                      />
                    </Field>
                  ) : null}
                </div>
              );
            })}

            <Button type="button" variant="outline" size="sm" onClick={addTender} className="self-start">
              <Plus className="size-4" />
              Split across another method
            </Button>
          </div>
        )}

        <div className="flex flex-col gap-3 rounded-md border p-3">
          <Field label="Coupon code" htmlFor="pos-coupon" hint="Validated by the server.">
            <div className="flex items-center gap-2">
              <Input
                id="pos-coupon"
                value={couponCode}
                onChange={(event) => onCouponChange(event.target.value.toUpperCase())}
                placeholder="e.g. SAVE10"
                autoComplete="off"
              />
              {couponCode ? (
                <Button type="button" variant="ghost" size="sm" onClick={() => onCouponChange("")}>
                  Clear
                </Button>
              ) : null}
            </div>
          </Field>

          {previewQuery.data ? (
            <div className="flex flex-col gap-1 text-sm">
              {previewQuery.data.applied.length === 0 ? (
                <span className="text-muted-foreground">No discounts apply to this cart.</span>
              ) : (
                previewQuery.data.applied.map((row) => (
                  <div
                    key={`${row.code ?? "auto"}-${row.name}`}
                    className="flex items-center justify-between"
                  >
                    <span className="text-muted-foreground">
                      {row.code ? `${row.code} · ` : ""}
                      {row.name}
                    </span>
                    <span className="tabular-nums">− {money(Number(row.amount), currency)}</span>
                  </div>
                ))
              )}
              {Number(previewQuery.data.total_discount) > 0 ? (
                <div className="flex items-center justify-between border-t pt-1 font-medium">
                  <span>Discount total</span>
                  <span className="tabular-nums">
                    − {money(Number(previewQuery.data.total_discount), currency)}
                  </span>
                </div>
              ) : null}
            </div>
          ) : null}

          {couponCode && previewQuery.isError ? (
            <p className="text-destructive text-sm">{describeError(previewQuery.error)}</p>
          ) : null}
        </div>

        <div className="flex flex-col gap-1 rounded-md border p-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Applied</span>
            <span className="tabular-nums">{money(applied, currency)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Still due</span>
            <span className="tabular-nums">{money(due, currency)}</span>
          </div>
          <div className="flex items-center justify-between font-medium">
            <span>Change</span>
            <span className="tabular-nums">{money(change, currency)}</span>
          </div>
        </div>

        <Field label="Note" htmlFor="sale-note" hint="Optional. Prints on the receipt.">
          <Input
            id="sale-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="e.g. delivery"
            autoComplete="off"
          />
        </Field>

        {blocking ? (
          <p className="text-warning-foreground flex items-start gap-2 text-sm">
            <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
            {blocking}
          </p>
        ) : null}
        {error ? <p className="text-destructive text-sm">{error}</p> : null}

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={mutation.isPending}
          >
            Back to cart
          </Button>
          <Button
            type="button"
            onClick={() => {
              setError(null);
              mutation.mutate();
            }}
            disabled={Boolean(blocking) || mutation.isPending || shown.length === 0}
          >
            {mutation.isPending ? "Completing…" : `Complete sale · ${money(payable, currency)}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
