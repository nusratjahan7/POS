import { Badge } from "@/components/ui/badge";
import type { PaymentStatus, SaleStatus } from "@/lib/api/sales";
import { paymentStatusOf } from "@/lib/sales/status";

type BadgeVariant = "success" | "warning" | "destructive" | "outline";

const SALE_STATUS: Record<SaleStatus, { label: string; variant: BadgeVariant }> = {
  completed: { label: "Completed", variant: "success" },
  refunded: { label: "Refunded", variant: "destructive" },
  voided: { label: "Voided", variant: "outline" },
};

const PAYMENT_STATUS: Record<PaymentStatus, { label: string; variant: BadgeVariant }> = {
  paid: { label: "Paid", variant: "success" },
  partial: { label: "Partial", variant: "warning" },
  unpaid: { label: "Unpaid", variant: "destructive" },
};

/** The single rendering of a sale's lifecycle status, shared list + detail. */
export function SaleStatusBadge({ status }: { status: SaleStatus }) {
  const badge = SALE_STATUS[status] ?? { label: status, variant: "outline" as const };
  return <Badge variant={badge.variant}>{badge.label}</Badge>;
}

/** The single rendering of a sale's settlement state, derived from its figures. */
export function PaymentStatusBadge({ sale }: { sale: { paid: string; due: string } }) {
  const badge = PAYMENT_STATUS[paymentStatusOf(sale)];
  return <Badge variant={badge.variant}>{badge.label}</Badge>;
}
