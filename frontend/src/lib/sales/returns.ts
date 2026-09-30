/**
 * The Return dialog's refund arithmetic, mirroring the server's.
 *
 * A line refunds its own net (after its line discount), proportionally for a
 * partial quantity — except when the return takes the last of the line, which
 * refunds exactly what is left of that net, so splitting a line across several
 * returns still adds up with no rounding drift. The running total is capped at
 * what the sale still has left to give back.
 *
 * This is a *preview* only: the server prices the refund authoritatively and its
 * figure is the one that is recorded.
 */

export type ReturnableLine = {
  saleItemId: string;
  productName: string;
  sku: string;
  unitPrice: number;
  /** Quantity sold. */
  sold: number;
  /** Quantity already returned. */
  returned: number;
  /** The sale line's net, after its own discount. */
  lineTotal: number;
  /** Refund value already given back for this line. */
  alreadyRefunded: number;
};

export type PlannedReturnLine = {
  saleItemId: string;
  quantity: number;
  refund: number;
};

export function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

export function remainingQuantity(line: ReturnableLine): number {
  return Math.max(line.sold - line.returned, 0);
}

export function planReturn(
  lines: ReturnableLine[],
  selections: Record<string, number>,
  remainingRefundable: number,
): { lines: PlannedReturnLine[]; total: number } {
  let cap = remainingRefundable;
  let total = 0;
  const planned: PlannedReturnLine[] = [];

  for (const line of lines) {
    const remaining = remainingQuantity(line);
    const quantity = Math.min(selections[line.saleItemId] ?? 0, remaining);
    if (quantity <= 0) continue;

    const refund =
      quantity >= remaining
        ? roundMoney(line.lineTotal - line.alreadyRefunded)
        : roundMoney((quantity * line.lineTotal) / line.sold);

    const capped = Math.min(refund, cap);
    cap = roundMoney(cap - capped);
    total = roundMoney(total + capped);
    planned.push({ saleItemId: line.saleItemId, quantity, refund: capped });
  }

  return { lines: planned, total };
}

/**
 * How a refund splits: goods the customer never paid for clear the debt first,
 * and only the rest is paid back.
 */
export function splitRefund(
  refund: number,
  saleDue: number,
  alreadyReturned: number,
): { credited: number; cash: number } {
  const outstanding = roundMoney(Math.max(saleDue - Math.min(alreadyReturned, saleDue), 0));
  const credited = Math.min(refund, outstanding);
  return { credited: roundMoney(credited), cash: roundMoney(refund - credited) };
}
