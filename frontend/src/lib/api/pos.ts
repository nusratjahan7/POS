import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

export type PosStockStatus = "in_stock" | "low_stock" | "out_of_stock";

export type PosProduct = {
  id: string;
  name: string;
  sku: string;
  barcode: string | null;
  unit: string;
  selling_price: string;
  discount_price: string | null;
  image_url: string | null;
  category_id: string | null;
  /** On-hand quantity at the selected branch. */
  stock_quantity: string;
  stock_status: PosStockStatus;
};

export type PosCategory = {
  id: string;
  name: string;
  slug: string;
  product_count: number;
};

export type PosStock = {
  product_id: string;
  stock_quantity: string;
  stock_status: PosStockStatus;
};

export type PosCatalogParams = {
  branch_id?: string;
  search?: string;
  sku?: string;
  barcode?: string;
  category_id?: string;
  page?: number;
  page_size?: number;
};

export const posApi = {
  catalog(params: PosCatalogParams = {}): Promise<Page<PosProduct>> {
    return apiRequest<Page<PosProduct>>(withQuery("/pos/catalog", { page_size: 40, ...params }));
  },

  categories(): Promise<PosCategory[]> {
    return apiRequest<PosCategory[]>("/pos/categories");
  },

  /** On-hand stock for a set of products at a branch — the till's cart cap. */
  stock(params: { branch_id?: string; ids: string[] }): Promise<PosStock[]> {
    const search = new URLSearchParams();
    if (params.branch_id) search.set("branch_id", params.branch_id);
    for (const id of params.ids) search.append("ids", id);
    const query = search.toString();
    return apiRequest<PosStock[]>(`/pos/stock${query ? `?${query}` : ""}`);
  },
};
