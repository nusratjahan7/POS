import { apiRequest } from "@/lib/api/client";
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
  sort?: string;
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
};
