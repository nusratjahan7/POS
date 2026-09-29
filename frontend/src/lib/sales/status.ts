import type { PaymentStatus } from "@/lib/api/sales";

/**
 * A sale's settlement state, derived from its own figures.
 *
 * The backend stores neither status: `due = total - paid` is enforced by a CHECK
 * constraint, so the three states fall straight out of the arithmetic and can
 * never disagree with it.
 */
export function paymentStatusOf(sale: { paid: string; due: string }): PaymentStatus {
  if (Number(sale.due) <= 0) return "paid";
  return Number(sale.paid) > 0 ? "partial" : "unpaid";
}
