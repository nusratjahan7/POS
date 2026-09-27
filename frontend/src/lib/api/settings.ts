import { apiRequest, apiUpload } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

/** The trading entity's profile, currency, time zone and tax settings. */
export type Business = {
  id: string;
  name: string;
  logo_url: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  currency: string;
  timezone: string;
  tax_enabled: boolean;
  tax_inclusive: boolean;
  tax_label: string;
  default_tax_rate: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type BusinessPayload = {
  name?: string;
  logo_url?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  currency?: string;
  timezone?: string;
  tax_enabled?: boolean;
  tax_inclusive?: boolean;
  tax_label?: string;
  default_tax_rate?: string;
  is_active?: boolean;
};

export type Register = {
  id: string;
  name: string;
  branch_id: string;
  branch: { id: string; name: string; code: string };
  is_active: boolean;
  default_opening_balance: string;
  require_opening_balance: boolean;
  allow_opening_balance_override: boolean;
  created_at: string;
  updated_at: string;
};

export type RegisterPayload = {
  name: string;
  branch_id: string;
  is_active?: boolean;
  default_opening_balance?: string;
  require_opening_balance?: boolean;
  allow_opening_balance_override?: boolean;
};

export type RegisterOption = {
  id: string;
  name: string;
  branch_id: string;
};

export type PaymentKind = "cash" | "card" | "mobile" | "bank" | "other";

export type PaymentMethod = {
  id: string;
  name: string;
  code: string;
  kind: PaymentKind;
  description: string | null;
  is_active: boolean;
  opens_cash_drawer: boolean;
  requires_reference: boolean;
  is_system: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type PaymentMethodPayload = {
  name: string;
  code: string;
  kind: PaymentKind;
  description?: string | null;
  is_active?: boolean;
  opens_cash_drawer?: boolean;
  requires_reference?: boolean;
  sort_order?: number;
};

export const businessApi = {
  get(): Promise<Business> {
    return apiRequest<Business>("/business");
  },

  update(payload: BusinessPayload): Promise<Business> {
    return apiRequest<Business>("/business", { method: "PATCH", body: payload });
  },
};

export const registersApi = {
  list(
    params: { page?: number; page_size?: number; search?: string; branch_id?: string } = {},
  ): Promise<Page<Register>> {
    return apiRequest<Page<Register>>(withQuery("/registers", { page_size: 100, ...params }));
  },

  options(branchId?: string): Promise<RegisterOption[]> {
    return apiRequest<RegisterOption[]>(withQuery("/registers/options", { branch_id: branchId }));
  },

  create(payload: RegisterPayload): Promise<Register> {
    return apiRequest<Register>("/registers", { method: "POST", body: payload });
  },

  update(registerId: string, payload: Partial<RegisterPayload>): Promise<Register> {
    return apiRequest<Register>(`/registers/${registerId}`, { method: "PATCH", body: payload });
  },

  remove(registerId: string): Promise<void> {
    return apiRequest<void>(`/registers/${registerId}`, { method: "DELETE" });
  },
};

export const paymentMethodsApi = {
  list(params: { page?: number; page_size?: number; search?: string } = {}): Promise<
    Page<PaymentMethod>
  > {
    return apiRequest<Page<PaymentMethod>>(
      withQuery("/payment-methods", { page_size: 100, ...params }),
    );
  },

  create(payload: PaymentMethodPayload): Promise<PaymentMethod> {
    return apiRequest<PaymentMethod>("/payment-methods", { method: "POST", body: payload });
  },

  update(methodId: string, payload: Partial<PaymentMethodPayload>): Promise<PaymentMethod> {
    return apiRequest<PaymentMethod>(`/payment-methods/${methodId}`, {
      method: "PATCH",
      body: payload,
    });
  },

  remove(methodId: string): Promise<void> {
    return apiRequest<void>(`/payment-methods/${methodId}`, { method: "DELETE" });
  },
};

export const uploadsApi = {
  /** Upload an image and receive its site-relative URL. */
  async uploadImage(file: File): Promise<{ url: string; content_type: string; size: number }> {
    const formData = new FormData();
    formData.append("file", file);
    return apiUpload<{ url: string; content_type: string; size: number }>(
      "/uploads/images",
      formData,
    );
  },
};
