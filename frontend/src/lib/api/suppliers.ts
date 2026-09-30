import { apiRequest } from "@/lib/api/client";
import type { LedgerParams, LedgerStatement } from "@/lib/api/ledger";
import { withQuery, type Page } from "@/lib/api/rbac";

export type Supplier = {
  id: string;
  name: string;
  company: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  opening_balance: string;
  /** Current amount owed to this supplier. */
  balance: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SupplierOption = {
  id: string;
  name: string;
  balance: string;
};

export type SupplierPayload = {
  name: string;
  company?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  /** Only honoured on create. */
  opening_balance?: string;
  is_active?: boolean;
};

export type SupplierListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  /** Only suppliers we still owe money (outstanding payable). */
  has_dues?: boolean;
  sort?: string;
};

/** A payment made to a supplier against what we owe them. */
export type SupplierPayment = {
  id: string;
  amount: string;
  method: string | null;
  reference: string | null;
  note: string | null;
  user: { id: string; full_name: string } | null;
  paid_at: string;
};

export type SupplierPaymentPayload = {
  amount: string;
  method?: string | null;
  reference?: string | null;
  note?: string | null;
};

export const suppliersApi = {
  list(params: SupplierListParams = {}): Promise<Page<Supplier>> {
    return apiRequest<Page<Supplier>>(withQuery("/suppliers", { page_size: 20, ...params }));
  },

  options(): Promise<SupplierOption[]> {
    return apiRequest<SupplierOption[]>("/suppliers/options");
  },

  create(payload: SupplierPayload): Promise<Supplier> {
    return apiRequest<Supplier>("/suppliers", { method: "POST", body: payload });
  },

  update(supplierId: string, payload: Partial<SupplierPayload>): Promise<Supplier> {
    return apiRequest<Supplier>(`/suppliers/${supplierId}`, { method: "PATCH", body: payload });
  },

  remove(supplierId: string): Promise<void> {
    return apiRequest<void>(`/suppliers/${supplierId}`, { method: "DELETE" });
  },

  /** Payments made to a supplier, newest first. */
  listPayments(
    supplierId: string,
    params: { page?: number; page_size?: number } = {},
  ): Promise<Page<SupplierPayment>> {
    return apiRequest<Page<SupplierPayment>>(
      withQuery(`/suppliers/${supplierId}/payments`, { page_size: 20, ...params }),
    );
  },

  /** Pay down what we owe a supplier. Rejected if it exceeds the balance. */
  recordPayment(supplierId: string, payload: SupplierPaymentPayload): Promise<SupplierPayment> {
    return apiRequest<SupplierPayment>(`/suppliers/${supplierId}/payments`, {
      method: "POST",
      body: payload,
    });
  },

  /** The supplier's account statement (date, reference, debit, credit, balance). */
  ledger(supplierId: string, params: LedgerParams = {}): Promise<LedgerStatement> {
    return apiRequest<LedgerStatement>(
      withQuery(`/suppliers/${supplierId}/ledger`, { ...params }),
    );
  },
};
