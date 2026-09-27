"use client";

import * as React from "react";
import { Clock, Percent, Receipt, ShoppingBag } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { CartTotals, HeldCart, PosCustomer } from "@/lib/pos/cart-store";
import { formatMoney, formatQuantity } from "@/lib/format";

// --- Order discount --------------------------------------------------------
export function PosDiscountDialog({
  value,
  subtotal,
  currency,
  onApply,
  onClose,
}: {
  value: number;
  subtotal: number;
  currency: string;
  onApply: (amount: number) => void;
  onClose: () => void;
}) {
  const [amount, setAmount] = React.useState(value === 0 ? "" : String(value));
  const [error, setError] = React.useState<string | null>(null);

  function apply() {
    const parsed = Number(amount) || 0;
    if (parsed < 0) {
      setError("The discount cannot be negative.");
      return;
    }
    if (parsed > subtotal) {
      setError("The discount cannot exceed the subtotal.");
      return;
    }
    onApply(parsed);
    onClose();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Order discount</DialogTitle>
          <DialogDescription>
            Subtotal is {formatMoney(subtotal, currency)}.
          </DialogDescription>
        </DialogHeader>

        <Field label="Discount amount" htmlFor="order-discount" error={error}>
          <Input
            id="order-discount"
            autoFocus
            inputMode="decimal"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="0.00"
            className="tabular-nums"
          />
        </Field>

        <div className="flex flex-wrap gap-2">
          {[5, 10, 20].map((percent) => (
            <Button
              key={percent}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setAmount(((subtotal * percent) / 100).toFixed(2))}
            >
              <Percent className="size-3.5" />
              {percent}%
            </Button>
          ))}
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" onClick={apply}>
            Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- Hold ------------------------------------------------------------------
export function PosHoldDialog({
  onHold,
  onClose,
}: {
  onHold: (label: string) => void;
  onClose: () => void;
}) {
  const [label, setLabel] = React.useState("");

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Hold this sale</DialogTitle>
          <DialogDescription>
            Park the cart and start a new one; resume it from Held sales.
          </DialogDescription>
        </DialogHeader>

        <Field label="Label" htmlFor="hold-label" hint="Optional — helps you find it later.">
          <Input
            id="hold-label"
            autoFocus
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="e.g. Table 4"
            autoComplete="off"
          />
        </Field>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => {
              onHold(label);
              onClose();
            }}
          >
            <Clock className="size-4" />
            Hold sale
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- Held sales ------------------------------------------------------------
export function PosHeldListDialog({
  held,
  currency,
  onResume,
  onDrop,
  onClose,
}: {
  held: readonly HeldCart[];
  currency: string;
  onResume: (id: string) => void;
  onDrop: (id: string) => void;
  onClose: () => void;
}) {
  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Held sales</DialogTitle>
          <DialogDescription>Resume a parked cart, or discard it.</DialogDescription>
        </DialogHeader>

        {held.length === 0 ? (
          <EmptyState
            icon={Clock}
            size="compact"
            title="Nothing on hold"
            description="Carts you hold will show up here."
          />
        ) : (
          <ul className="flex max-h-80 flex-col gap-2 overflow-y-auto">
            {held.map((cart) => {
              const total = cart.lines.reduce(
                (sum, line) => sum + line.unitPrice * line.quantity - line.discount,
                0,
              );
              return (
                <li
                  key={cart.id}
                  className="flex items-center justify-between gap-3 rounded-md border p-3"
                >
                  <div className="flex min-w-0 flex-col">
                    <span className="truncate text-sm font-medium">{cart.label}</span>
                    <span className="text-muted-foreground text-xs">
                      {cart.lines.length} line{cart.lines.length === 1 ? "" : "s"} ·{" "}
                      {formatQuantity(cart.lines.reduce((n, line) => n + line.quantity, 0))} items
                      {cart.customer ? ` · ${cart.customer.name}` : ""}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant="neutral">{formatMoney(Math.max(total, 0), currency)}</Badge>
                    <Button size="sm" onClick={() => onResume(cart.id)}>
                      Resume
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onDrop(cart.id)}>
                      Discard
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}

// --- Checkout (Module 11) --------------------------------------------------
export function PosCheckoutDialog({
  totals,
  customer,
  currency,
  onClose,
}: {
  totals: CartTotals;
  customer: PosCustomer | null;
  currency: string;
  onClose: () => void;
}) {
  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Ready to check out</DialogTitle>
          <DialogDescription>
            Payment and finalising the sale arrive in Module 11. Nothing has been saved yet.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2 rounded-md border p-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Customer</span>
            <span>{customer ? customer.name : "Walk-in"}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Items</span>
            <span className="tabular-nums">{formatQuantity(totals.itemCount)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Subtotal</span>
            <span className="tabular-nums">{formatMoney(totals.subtotal, currency)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Discount</span>
            <span className="tabular-nums">{formatMoney(totals.discountTotal, currency)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Tax</span>
            <span className="tabular-nums">{formatMoney(totals.tax, currency)}</span>
          </div>
          <div className="flex items-center justify-between border-t pt-2 text-base font-semibold">
            <span>Grand total</span>
            <span className="tabular-nums">{formatMoney(totals.total, currency)}</span>
          </div>
        </div>

        <div className="text-muted-foreground flex items-start gap-2 text-xs">
          <ShoppingBag className="mt-px size-3.5 shrink-0" aria-hidden />
          The cart is kept in this browser, so you can keep scanning without losing it.
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Continue selling
          </Button>
          <Button type="button" disabled>
            <Receipt className="size-4" />
            Take payment (Module 11)
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
