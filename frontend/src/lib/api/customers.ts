import { apiRequest } from "@/lib/api/client";
import type { LedgerParams, LedgerStatement } from "@/lib/api/ledger";
import { withQuery, type Page } from "@/lib/api/rbac";

export type Customer = {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  opening_balance: string;
  /** Amount the customer currently owes. */
  balance: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type CustomerOption = {
  id: string;
  name: string;
  balance: string;
};

export type CustomerPayload = {
  name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  /** Only honoured on create. */
  opening_balance?: string;
  is_active?: boolean;
};

export type CustomerPayment = {
  id: string;
  amount: string;
  method: string | null;
  reference: string | null;
  note: string | null;
  user: { id: string; full_name: string } | null;
  paid_at: string;
};

export type CustomerPaymentPayload = {
  amount: string;
  method?: string | null;
  reference?: string | null;
  note?: string | null;
};

/** A sale summary — empty until the sales module ships. */
export type CustomerPurchase = {
  id: string;
  reference: string;
  purchased_at: string;
  total: string;
  paid: string;
  due: string;
};

export type CustomerDetails = {
  customer: Customer;
  total_orders: number;
  total_purchase_amount: string;
  total_paid: string;
  outstanding_due: string;
  recent_payments: CustomerPayment[];
  recent_purchases: CustomerPurchase[];
};

export type CustomerListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  /** Only customers who still owe something (outstanding balance). */
  has_dues?: boolean;
  sort?: string;
};

export const customersApi = {
  list(params: CustomerListParams = {}): Promise<Page<Customer>> {
    return apiRequest<Page<Customer>>(withQuery("/customers", { page_size: 20, ...params }));
  },

  options(): Promise<CustomerOption[]> {
    return apiRequest<CustomerOption[]>("/customers/options");
  },

  get(customerId: string): Promise<Customer> {
    return apiRequest<Customer>(`/customers/${customerId}`);
  },

  details(customerId: string): Promise<CustomerDetails> {
    return apiRequest<CustomerDetails>(`/customers/${customerId}/details`);
  },

  create(payload: CustomerPayload): Promise<Customer> {
    return apiRequest<Customer>("/customers", { method: "POST", body: payload });
  },

  update(customerId: string, payload: Partial<CustomerPayload>): Promise<Customer> {
    return apiRequest<Customer>(`/customers/${customerId}`, { method: "PATCH", body: payload });
  },

  deactivate(customerId: string): Promise<void> {
    return apiRequest<void>(`/customers/${customerId}`, { method: "DELETE" });
  },

  listPayments(
    customerId: string,
    params: { page?: number; page_size?: number } = {},
  ): Promise<Page<CustomerPayment>> {
    return apiRequest<Page<CustomerPayment>>(
      withQuery(`/customers/${customerId}/payments`, { page_size: 20, ...params }),
    );
  },

  recordPayment(customerId: string, payload: CustomerPaymentPayload): Promise<CustomerPayment> {
    return apiRequest<CustomerPayment>(`/customers/${customerId}/payments`, {
      method: "POST",
      body: payload,
    });
  },

  listPurchases(customerId: string): Promise<CustomerPurchase[]> {
    return apiRequest<CustomerPurchase[]>(`/customers/${customerId}/purchases`);
  },

  /** The customer's account statement (date, reference, debit, credit, balance). */
  ledger(customerId: string, params: LedgerParams = {}): Promise<LedgerStatement> {
    return apiRequest<LedgerStatement>(
      withQuery(`/customers/${customerId}/ledger`, { ...params }),
    );
  },
};
