"use client";

import * as React from "react";
import { Hash, Minus, Plus, ShoppingCart, Trash2, UserRound, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import type { CartLine, CartTotals, PosCustomer } from "@/lib/pos/cart-store";
import { formatMoney, formatQuantity } from "@/lib/format";
import { cn } from "@/lib/utils";

type PosCartProps = {
  lines: readonly CartLine[];
  customer: PosCustomer | null;
  totals: CartTotals;
  currency: string;
  heldCount: number;
  onQuantity: (productId: string, quantity: number) => void;
  onLineDiscount: (productId: string, amount: number) => void;
  onRemove: (productId: string) => void;
  onCustomer: () => void;
  onDiscount: () => void;
  onHold: () => void;
  onClear: () => void;
  onCheckout: () => void;
  onHeld: () => void;
};

export function PosCart({
  lines,
  customer,
  totals,
  currency,
  heldCount,
  onQuantity,
  onLineDiscount,
  onRemove,
  onCustomer,
  onDiscount,
  onHold,
  onClear,
  onCheckout,
  onHeld,
}: PosCartProps) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Customer */}
      <button
        type="button"
        onClick={onCustomer}
        className="hover:bg-accent/60 focus-visible:ring-ring/60 flex items-center gap-2 border-b px-4 py-3 text-left transition-colors outline-none focus-visible:ring-2"
      >
        <UserRound className="text-muted-foreground size-4 shrink-0" aria-hidden />
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-medium">
            {customer ? customer.name : "Walk-in customer"}
          </span>
          {customer?.balance ? (
            <span className="text-muted-foreground text-xs">
              Owes {formatMoney(customer.balance, currency)}
            </span>
          ) : null}
        </span>
        <span className="text-muted-foreground text-xs">Change</span>
      </button>

      {/* Lines */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {lines.length === 0 ? (
          <EmptyState
            icon={ShoppingCart}
            size="compact"
            title="Cart is empty"
            description="Search or scan a product to add it."
          />
        ) : (
          <ul className="divide-y">
            {lines.map((line) => (
              <li key={line.productId} className="flex flex-col gap-2 px-4 py-3">
                <div className="flex items-start gap-2">
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">{line.name}</span>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => onRemove(line.productId)}
                    aria-label={`Remove ${line.name}`}
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>

                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => onQuantity(line.productId, Math.max(1, line.quantity - 1))}
                      aria-label="Decrease quantity"
                    >
                      <Minus className="size-3.5" />
                    </Button>
                    <Input
                      inputMode="decimal"
                      value={String(line.quantity)}
                      onChange={(event) =>
                        onQuantity(line.productId, Math.max(1, Number(event.target.value) || 1))
                      }
                      aria-label={`Quantity for ${line.name}`}
                      className="h-8 w-14 text-center tabular-nums"
                    />
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => onQuantity(line.productId, line.quantity + 1)}
                      aria-label="Increase quantity"
                    >
                      <Plus className="size-3.5" />
                    </Button>
                  </div>

                  <span className="text-muted-foreground min-w-0 truncate text-xs tabular-nums">
                    {formatMoney(line.unitPrice, currency)} × {formatQuantity(line.quantity)}
                  </span>

                  <span className="ml-auto w-20 shrink-0 text-right text-sm font-medium tabular-nums">
                    {formatMoney(line.unitPrice * line.quantity - line.discount, currency)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <label
                    htmlFor={`discount-${line.productId}`}
                    className="text-muted-foreground flex items-center gap-1 text-xs"
                  >
                    <Hash className="size-3" aria-hidden />
                    Discount
                  </label>
                  <Input
                    id={`discount-${line.productId}`}
                    inputMode="decimal"
                    value={line.discount === 0 ? "" : String(line.discount)}
                    placeholder="0.00"
                    onChange={(event) =>
                      onLineDiscount(line.productId, Math.max(0, Number(event.target.value) || 0))
                    }
                    className="h-7 w-20 tabular-nums"
                  />
                  <span className="text-muted-foreground ml-auto text-xs tabular-nums">
                    {formatQuantity(Math.max(line.limit - line.quantity, 0))} left
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Totals */}
      <div className="flex flex-col gap-1.5 border-t px-4 py-3 text-sm">
        <Row label={`Subtotal (${formatQuantity(totals.itemCount)} items)`} value={totals.subtotal} currency={currency} />
        <Row label="Discount" value={-totals.discountTotal} currency={currency} />
        <Row label="Tax" value={totals.tax} currency={currency} />
        <div className="mt-1 flex items-center justify-between border-t pt-2 text-base font-semibold">
          <span>Grand total</span>
          <span className="tabular-nums">{formatMoney(totals.total, currency)}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 border-t px-4 py-3">
        <div className="grid grid-cols-3 gap-2">
          <Button variant="outline" size="sm" onClick={onCustomer}>
            <UserRound className="size-4" />
            Customer
          </Button>
          <Button variant="outline" size="sm" onClick={onDiscount} disabled={lines.length === 0}>
            <Hash className="size-4" />
            Discount
          </Button>
          <Button variant="outline" size="sm" onClick={onHold} disabled={lines.length === 0}>
            Hold
            {heldCount > 0 ? <Badge variant="neutral">{heldCount}</Badge> : null}
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Button variant="ghost" size="sm" onClick={onClear} disabled={lines.length === 0}>
            <Trash2 className="size-4" />
            Clear
          </Button>
          <Button variant="subtle" size="sm" onClick={onHeld}>
            Held sales
          </Button>
        </div>

        <Button size="lg" onClick={onCheckout} disabled={lines.length === 0} className="w-full">
          Checkout · {formatMoney(totals.total, currency)}
        </Button>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  currency,
}: {
  label: string;
  value: number;
  currency: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("tabular-nums", value < 0 && "text-destructive")}>
        {formatMoney(value, currency)}
      </span>
    </div>
  );
}
