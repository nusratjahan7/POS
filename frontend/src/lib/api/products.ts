import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

/** Minimal category/brand reference embedded in a product response. */
export type ProductRef = {
  id: string;
  name: string;
  slug: string;
};

export type StockStatus = "in_stock" | "low_stock" | "out_of_stock";

export type Product = {
  id: string;
  name: string;
  slug: string;
  sku: string;
  barcode: string | null;
  category_id: string | null;
  brand_id: string | null;
  category: ProductRef | null;
  brand: ProductRef | null;
  purchase_price: string;
  selling_price: string;
  discount_price: string | null;
  unit: string;
  minimum_stock: string;
  stock_quantity: string;
  description: string | null;
  image_url: string | null;
  is_active: boolean;
  stock_status: StockStatus;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
};

export type ProductPayload = {
  name: string;
  sku: string;
  barcode?: string | null;
  category_id?: string | null;
  brand_id?: string | null;
  purchase_price?: string;
  selling_price?: string;
  discount_price?: string | null;
  unit?: string;
  minimum_stock?: string;
  /** Opening balance, only accepted on create. */
  opening_stock?: string;
  description?: string | null;
  image_url?: string | null;
  is_active?: boolean;
};

export type ProductListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  sku?: string;
  barcode?: string;
  category_id?: string;
  brand_id?: string;
  is_active?: boolean;
  sort?: string;
};

export const productsApi = {
  list(params: ProductListParams = {}): Promise<Page<Product>> {
    return apiRequest<Page<Product>>(withQuery("/products", { page_size: 20, ...params }));
  },

  create(payload: ProductPayload): Promise<Product> {
    return apiRequest<Product>("/products", { method: "POST", body: payload });
  },

  update(productId: string, payload: Partial<ProductPayload>): Promise<Product> {
    return apiRequest<Product>(`/products/${productId}`, { method: "PATCH", body: payload });
  },

  remove(productId: string): Promise<void> {
    return apiRequest<void>(`/products/${productId}`, { method: "DELETE" });
  },
};
