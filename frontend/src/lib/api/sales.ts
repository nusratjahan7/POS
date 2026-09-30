import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

/** Money and quantities travel as strings so no precision is lost in transit. */
export type SaleItemInput = {
  product_id: string;
  quantity: string;
  discount?: string;
};

export type SalePaymentInput = {
  payment_method_id: string;
  amount: string;
  /** Cash handed over; anything above `amount` comes back as change. */
  tendered?: string | null;
  reference?: string | null;
  note?: string | null;
};

/**
 * What the till posts to complete a sale.
 *
 * There is deliberately no price or total here: the server resolves every price
 * and computes the discount, tax and grand total itself.
 */
export type SaleCreatePayload = {
  branch_id: string;
  register_id?: string | null;
  customer_id?: string | null;
  note?: string | null;
  order_discount?: string;
  items: SaleItemInput[];
  payments: SalePaymentInput[];
};

export type SaleItem = {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  unit: string;
  quantity: string;
  unit_price: string;
  discount: string;
  subtotal: string;
  line_total: string;
};

export type SalePaymentMethod = {
  id: string;
  name: string;
  code: string;
  kind: string;
};

export type SalePayment = {
  id: string;
  payment_method: SalePaymentMethod;
  amount: string;
  tendered: string | null;
  change_given: string;
  reference: string | null;
  note: string | null;
  paid_at: string;
};

export type Sale = {
  id: string;
  sale_number: string;
  branch: { id: string; name: string };
  register_id: string | null;
  customer: { id: string; name: string; balance: string } | null;
  cashier: { id: string; full_name: string } | null;
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
  paid: string;
  due: string;
  change_amount: string;
  /** What the customer handed over: paid plus the change given back. */
  received_amount: string;
  status: SaleStatus;
  note: string | null;
  items: SaleItem[];
  payments: SalePayment[];
  sold_at: string;
  created_at: string;
  /** Value of goods returned so far, across every completed return. */
  returned_amount: string;
  refunded_at: string | null;
  refunded_by: { id: string; full_name: string } | null;
  refund_reason: string | null;
};

export type SaleReceipt = {
  business: {
    name: string;
    logo_url: string | null;
    phone: string | null;
    email: string | null;
    address: string | null;
    currency: string;
    tax_label: string;
  };
  /** The branch the sale happened at, with the contact details a receipt shows. */
  branch: {
    id: string;
    name: string;
    code: string;
    address: string | null;
    phone: string | null;
  };
  sale: Sale;
};

export type SaleStatus = "completed" | "voided" | "refunded";

/** Settlement state, derived server-side from `paid`/`due`. */
export type PaymentStatus = "paid" | "partial" | "unpaid";

/** A sale row as the management list returns it — no line items or tenders. */
export type SaleSummary = {
  id: string;
  sale_number: string;
  branch: { id: string; name: string; code: string };
  customer: { id: string; name: string; balance: string } | null;
  cashier: { id: string; full_name: string } | null;
  sold_at: string;
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
  paid: string;
  due: string;
  change_amount: string;
  /** What the customer handed over: paid plus the change given back. */
  received_amount: string;
  status: SaleStatus;
  item_count: number;
};

/** A cashier who has sales — the management screen's cashier filter. */
export type SaleCashierOption = {
  id: string;
  full_name: string;
};

export type SaleReturnStatus = "requested" | "approved" | "completed" | "cancelled";

export type SaleReturnItem = {
  id: string;
  sale_item_id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: string;
  unit_price: string;
  /** The refund this line carries. */
  line_total: string;
};

/** A return document: goods coming back from a sale, and the refund they carry. */
export type SaleReturn = {
  id: string;
  return_number: string;
  status: SaleReturnStatus;
  reason: string | null;
  note: string | null;
  refund_amount: string;
  /** The part of `refund_amount` that cleared what the customer still owed. */
  credit_reversed: string;
  /** The part actually paid back. */
  cash_refund: string;
  payment_method: SalePaymentMethod | null;
  refund_reference: string | null;
  created_by: { id: string; full_name: string } | null;
  completed_by: { id: string; full_name: string } | null;
  created_at: string;
  completed_at: string | null;
  cancelled_at: string | null;
  items: SaleReturnItem[];
};

export type SaleReturnItemInput = {
  sale_item_id: string;
  quantity: string;
};

/**
 * What the operator posts to hand goods back.
 *
 * No amounts: the server prices the refund from the sale line's own net.
 */
export type SaleReturnPayload = {
  items: SaleReturnItemInput[];
  reason?: string | null;
  note?: string | null;
  payment_method_id?: string | null;
  reference?: string | null;
};

export type SaleListParams = {
  page?: number;
  page_size?: number;
  /** Invoice number. */
  search?: string;
  branch_id?: string;
  customer_id?: string;
  cashier_id?: string;
  status?: SaleStatus;
  payment_status?: PaymentStatus;
  /** ISO `YYYY-MM-DD`, sold on or after. */
  date_from?: string;
  /** ISO `YYYY-MM-DD`, sold on or before. */
  date_to?: string;
  /** `field` or `-field` (descending): sale_number, sold_at, total, paid, due. */
  sort?: string;
};

export const salesApi = {
  /** Complete the sale. The server prices it and moves the stock. */
  create(payload: SaleCreatePayload): Promise<Sale> {
    return apiRequest<Sale>("/sales", { method: "POST", body: payload });
  },

  get(saleId: string): Promise<Sale> {
    return apiRequest<Sale>(`/sales/${saleId}`);
  },

  /** The sale plus the business details a printed receipt needs. */
  receipt(saleId: string): Promise<SaleReceipt> {
    return apiRequest<SaleReceipt>(`/sales/${saleId}/receipt`);
  },

  list(params: SaleListParams = {}): Promise<Page<SaleSummary>> {
    return apiRequest<Page<SaleSummary>>(withQuery("/sales", { page_size: 10, ...params }));
  },

  /** Cashiers who have sales, for the screen's filter (needs only `sales:read`). */
  cashierOptions(): Promise<SaleCashierOption[]> {
    return apiRequest<SaleCashierOption[]>("/sales/cashiers");
  },

  /** Return goods from a sale: restocks, refunds and updates the sale. */
  createReturn(saleId: string, payload: SaleReturnPayload): Promise<SaleReturn> {
    return apiRequest<SaleReturn>(`/sales/${saleId}/returns`, { method: "POST", body: payload });
  },

  /** A sale's return history, newest first. */
  listReturns(saleId: string): Promise<SaleReturn[]> {
    return apiRequest<SaleReturn[]>(`/sales/${saleId}/returns`);
  },

  /** Cancel a return that has not been applied yet. */
  cancelReturn(saleId: string, returnId: string): Promise<SaleReturn> {
    return apiRequest<SaleReturn>(`/sales/${saleId}/returns/${returnId}/cancel`, {
      method: "POST",
      body: {},
    });
  },
};
