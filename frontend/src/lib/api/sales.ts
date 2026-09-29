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
  status: SaleStatus;
  note: string | null;
  items: SaleItem[];
  payments: SalePayment[];
  sold_at: string;
  created_at: string;
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
  status: SaleStatus;
  item_count: number;
};

/** A cashier who has sales — the management screen's cashier filter. */
export type SaleCashierOption = {
  id: string;
  full_name: string;
};

export type SaleRefundPayload = {
  reason?: string | null;
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

  /** Reverse a completed sale: restock it, unwind any credit, mark it refunded. */
  refund(saleId: string, payload: SaleRefundPayload = {}): Promise<Sale> {
    return apiRequest<Sale>(`/sales/${saleId}/refund`, { method: "POST", body: payload });
  },
};
