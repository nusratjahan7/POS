import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

export type DiscountScope = "product" | "cart";
export type DiscountType = "percentage" | "fixed";

export type Discount = {
  id: string;
  name: string;
  /** Present = a coupon the till must quote; null = an automatic promotion. */
  code: string | null;
  scope: DiscountScope;
  type: DiscountType;
  value: string;
  min_order_amount: string;
  max_discount_amount: string | null;
  starts_at: string | null;
  expires_at: string | null;
  usage_limit: number | null;
  per_customer_limit: number | null;
  is_active: boolean;
  first_order_only: boolean;
  exclude_discounted: boolean;
  /** Reserved — no shipping in the app, so it changes nothing. */
  free_shipping: boolean;
  product_ids: string[];
  category_ids: string[];
  brand_ids: string[];
  redeemed_count: number;
  created_at: string;
  updated_at: string;
};

export type DiscountPayload = {
  name: string;
  code?: string | null;
  scope: DiscountScope;
  type: DiscountType;
  value: string;
  min_order_amount?: string;
  max_discount_amount?: string | null;
  starts_at?: string | null;
  expires_at?: string | null;
  usage_limit?: number | null;
  per_customer_limit?: number | null;
  is_active?: boolean;
  first_order_only?: boolean;
  exclude_discounted?: boolean;
  free_shipping?: boolean;
  product_ids?: string[];
  category_ids?: string[];
  brand_ids?: string[];
};

export type DiscountListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  scope?: DiscountScope;
  is_active?: boolean;
  coupons_only?: boolean;
  sort?: string;
};

// --- Server-computed pricing preview ---------------------------------------
export type DiscountLineResult = {
  product_id: string;
  automatic_discount: string;
  manual_discount: string;
  discount: string;
  line_total: string;
};

export type DiscountApplied = {
  code: string | null;
  name: string;
  amount: string;
};

export type PriceBreakdown = {
  lines: DiscountLineResult[];
  subtotal: string;
  line_discounts: string;
  automatic_discount: string;
  coupon_discount: string;
  order_discount: string;
  total_discount: string;
  net: string;
  /** Tax on the net, and the amount actually payable. */
  tax: string;
  total: string;
  coupon: DiscountApplied | null;
  applied: DiscountApplied[];
};

export type DiscountPreviewRequest = {
  customer_id?: string | null;
  items: { product_id: string; quantity: string; discount?: string }[];
  order_discount?: string;
  coupon_code?: string | null;
};

export const discountsApi = {
  list(params: DiscountListParams = {}): Promise<Page<Discount>> {
    return apiRequest<Page<Discount>>(withQuery("/discounts", { page_size: 20, ...params }));
  },

  get(discountId: string): Promise<Discount> {
    return apiRequest<Discount>(`/discounts/${discountId}`);
  },

  create(payload: DiscountPayload): Promise<Discount> {
    return apiRequest<Discount>("/discounts", { method: "POST", body: payload });
  },

  update(discountId: string, payload: Partial<DiscountPayload>): Promise<Discount> {
    return apiRequest<Discount>(`/discounts/${discountId}`, { method: "PATCH", body: payload });
  },

  remove(discountId: string): Promise<void> {
    return apiRequest<void>(`/discounts/${discountId}`, { method: "DELETE" });
  },

  /**
   * Preview a basket's discounts. This never persists anything — the sale itself
   * is priced again, server-side, when it is created.
   */
  validate(payload: DiscountPreviewRequest): Promise<PriceBreakdown> {
    return apiRequest<PriceBreakdown>("/discounts/validate", { method: "POST", body: payload });
  },
};
