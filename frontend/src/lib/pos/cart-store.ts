"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Client-side cart for the till.
 *
 * Persisted to localStorage so the cashier can search, re-order and switch tabs
 * without a round-trip. Nothing is finalised until Module 11, which will post the
 * cart to the sales API; this store is the shape that call will read.
 *
 * Quantities are capped at `limit` — the product's stock at the selected branch.
 * The cap is a **UX guard only**; the authoritative check happens on the server
 * when the sale is created (see the sales service).
 */

export type CartLine = {
  productId: string;
  name: string;
  sku: string;
  unit: string;
  /** Effective unit price (discount price when set, otherwise selling price). */
  unitPrice: number;
  quantity: number;
  /** Line discount, as an amount off this line. */
  discount: number;
  /** Available stock at this line's branch — the maximum quantity allowed. */
  limit: number;
};

export type PosCustomer = {
  id: string | null;
  name: string;
  balance: string | null;
};

export type HeldCart = {
  id: string;
  label: string;
  createdAt: string;
  lines: CartLine[];
  customer: PosCustomer | null;
  orderDiscount: number;
};

export type AddResult =
  | { ok: true }
  | { ok: false; reason: "limit" | "out_of_stock"; available: number };

export type QuantityResult =
  | { ok: true; clamped: boolean; quantity: number }
  | { ok: false; reason: "out_of_stock"; available: number };

export type LimitAdjustment = { productId: string; name: string; from: number; to: number };
export type SyncResult = { adjusted: LimitAdjustment[]; removed: string[] };

type CartState = {
  branchId: string | null;
  customer: PosCustomer | null;
  lines: CartLine[];
  orderDiscount: number;
  held: HeldCart[];

  setBranch: (branchId: string | null) => void;
  addLine: (line: Omit<CartLine, "quantity" | "discount">, quantity?: number) => AddResult;
  setQuantity: (productId: string, quantity: number) => QuantityResult;
  setLineDiscount: (productId: string, discount: number) => void;
  removeLine: (productId: string) => void;
  setCustomer: (customer: PosCustomer | null) => void;
  setOrderDiscount: (amount: number) => void;
  /** Re-cap every line after a branch switch; over-limit lines are clamped. */
  syncLimits: (limits: Record<string, number>) => SyncResult;
  clear: () => void;

  hold: (label: string) => void;
  resume: (id: string) => void;
  dropHeld: (id: string) => void;
};

function newId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function normaliseQuantity(value: number): number {
  if (!Number.isFinite(value)) return 1;
  return Math.max(1, Math.floor(value));
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      branchId: null,
      customer: null,
      lines: [],
      orderDiscount: 0,
      held: [],

      setBranch: (branchId) => set({ branchId }),

      addLine: (line, quantity = 1) => {
        const state = get();
        const step = normaliseQuantity(quantity);
        const existing = state.lines.find((item) => item.productId === line.productId);
        // The freshest limit comes from the caller (the catalog fetch).
        const limit = Math.max(line.limit, 0);
        const current = existing?.quantity ?? 0;
        const desired = current + step;

        if (limit <= 0) return { ok: false, reason: "out_of_stock", available: 0 };
        if (desired > limit) return { ok: false, reason: "limit", available: limit };

        if (existing) {
          set({
            lines: state.lines.map((item) =>
              item.productId === line.productId
                ? { ...item, quantity: desired, limit }
                : item,
            ),
          });
        } else {
          set({ lines: [...state.lines, { ...line, limit, quantity: step, discount: 0 }] });
        }
        return { ok: true };
      },

      setQuantity: (productId, quantity) => {
        const state = get();
        const line = state.lines.find((item) => item.productId === productId);
        if (!line) return { ok: true, clamped: false, quantity };

        if (line.limit <= 0) return { ok: false, reason: "out_of_stock", available: 0 };

        const requested = normaliseQuantity(quantity);
        const capped = Math.min(requested, line.limit);
        set({
          lines: state.lines.map((item) =>
            item.productId === productId ? { ...item, quantity: capped } : item,
          ),
        });
        return { ok: true, clamped: capped !== requested, quantity: capped };
      },

      setLineDiscount: (productId, discount) =>
        set((state) => ({
          lines: state.lines.map((item) =>
            item.productId === productId ? { ...item, discount } : item,
          ),
        })),

      removeLine: (productId) =>
        set((state) => ({ lines: state.lines.filter((item) => item.productId !== productId) })),

      setCustomer: (customer) => set({ customer }),
      setOrderDiscount: (amount) => set({ orderDiscount: amount }),

      syncLimits: (limits) => {
        const state = get();
        const adjusted: LimitAdjustment[] = [];
        const removed: string[] = [];
        const lines: CartLine[] = [];

        for (const line of state.lines) {
          const limit = line.productId in limits ? Math.max(limits[line.productId] ?? 0, 0) : line.limit;
          if (limit <= 0) {
            adjusted.push({ productId: line.productId, name: line.name, from: line.quantity, to: 0 });
            removed.push(line.productId);
            continue;
          }
          if (line.quantity > limit) {
            adjusted.push({ productId: line.productId, name: line.name, from: line.quantity, to: limit });
            lines.push({ ...line, limit, quantity: limit });
          } else {
            lines.push({ ...line, limit });
          }
        }

        set({ lines });
        return { adjusted, removed };
      },

      clear: () => set({ lines: [], orderDiscount: 0, customer: null }),

      hold: (label) => {
        const { lines, customer, orderDiscount, held } = get();
        if (lines.length === 0) return;
        const entry: HeldCart = {
          id: newId(),
          label: label.trim() || `Hold ${held.length + 1}`,
          createdAt: new Date().toISOString(),
          lines,
          customer,
          orderDiscount,
        };
        set({ held: [entry, ...held], lines: [], orderDiscount: 0, customer: null });
      },

      resume: (id) => {
        const { held } = get();
        const entry = held.find((item) => item.id === id);
        if (!entry) return;
        set({
          lines: entry.lines,
          customer: entry.customer,
          orderDiscount: entry.orderDiscount,
          held: held.filter((item) => item.id !== id),
        });
      },

      dropHeld: (id) => set((state) => ({ held: state.held.filter((item) => item.id !== id) })),
    }),
    {
      name: "pos-cart",
      version: 2,
      // Rehydrated manually on mount so SSR and the first client render agree.
      skipHydration: true,
      // v1 lines carried `stockQuantity` instead of `limit`; drop them.
      migrate: (_persisted, version) =>
        version < 2
          ? { branchId: null, customer: null, lines: [], orderDiscount: 0, held: [] }
          : (_persisted as CartState),
    },
  ),
);

export type CartTotals = {
  subtotal: number;
  lineDiscounts: number;
  discountTotal: number;
  net: number;
  tax: number;
  total: number;
  itemCount: number;
};

/** Money maths for display. Exact decimals are the API's job at checkout. */
export function computeTotals(
  lines: readonly CartLine[],
  orderDiscount: number,
  tax: { enabled: boolean; inclusive: boolean; rate: number },
): CartTotals {
  const subtotal = lines.reduce((sum, line) => sum + line.unitPrice * line.quantity, 0);
  const lineDiscounts = lines.reduce((sum, line) => sum + line.discount, 0);
  const discountTotal = Math.min(lineDiscounts + Math.max(orderDiscount, 0), subtotal);
  const net = Math.max(subtotal - discountTotal, 0);

  let taxAmount = 0;
  if (tax.enabled && tax.rate > 0) {
    const rate = tax.rate / 100;
    taxAmount = tax.inclusive ? net - net / (1 + rate) : net * rate;
  }
  const total = tax.enabled && !tax.inclusive ? net + taxAmount : net;

  return {
    subtotal,
    lineDiscounts,
    discountTotal,
    net,
    tax: taxAmount,
    total,
    itemCount: lines.reduce((sum, line) => sum + line.quantity, 0),
  };
}
