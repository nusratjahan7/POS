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
  status: string;
  note: string | null;
  items: SaleItem[];
  payments: SalePayment[];
  sold_at: string;
  created_at: string;
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
  sale: Sale;
};

export type SaleListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  branch_id?: string;
  customer_id?: string;
  status?: string;
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

  list(params: SaleListParams = {}): Promise<Page<Sale>> {
    return apiRequest<Page<Sale>>(withQuery("/sales", { page_size: 20, ...params }));
  },
};
