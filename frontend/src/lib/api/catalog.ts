import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

export type CategoryRef = {
  id: string;
  name: string;
  slug: string;
};

export type Category = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  parent_id: string | null;
  parent: CategoryRef | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

/** A category and its descendants, as returned by `/categories/tree`. */
export type CategoryNode = {
  id: string;
  name: string;
  slug: string;
  image_url: string | null;
  parent_id: string | null;
  is_active: boolean;
  children: CategoryNode[];
};

export type CategoryPayload = {
  name: string;
  description?: string | null;
  image_url?: string | null;
  parent_id?: string | null;
  is_active?: boolean;
};

export type CategoryListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  parent_id?: string;
  top_level?: boolean;
  sort?: string;
};

export type Brand = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  logo_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type BrandPayload = {
  name: string;
  description?: string | null;
  logo_url?: string | null;
  is_active?: boolean;
};

export type BrandListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  sort?: string;
};

export const categoriesApi = {
  list(params: CategoryListParams = {}): Promise<Page<Category>> {
    return apiRequest<Page<Category>>(withQuery("/categories", { page_size: 20, ...params }));
  },

  tree(): Promise<CategoryNode[]> {
    return apiRequest<CategoryNode[]>("/categories/tree");
  },

  options(): Promise<CategoryRef[]> {
    return apiRequest<CategoryRef[]>("/categories/options");
  },

  create(payload: CategoryPayload): Promise<Category> {
    return apiRequest<Category>("/categories", { method: "POST", body: payload });
  },

  update(categoryId: string, payload: Partial<CategoryPayload>): Promise<Category> {
    return apiRequest<Category>(`/categories/${categoryId}`, { method: "PATCH", body: payload });
  },

  remove(categoryId: string): Promise<void> {
    return apiRequest<void>(`/categories/${categoryId}`, { method: "DELETE" });
  },
};

export const brandsApi = {
  list(params: BrandListParams = {}): Promise<Page<Brand>> {
    return apiRequest<Page<Brand>>(withQuery("/brands", { page_size: 20, ...params }));
  },

  options(): Promise<CategoryRef[]> {
    return apiRequest<CategoryRef[]>("/brands/options");
  },

  create(payload: BrandPayload): Promise<Brand> {
    return apiRequest<Brand>("/brands", { method: "POST", body: payload });
  },

  update(brandId: string, payload: Partial<BrandPayload>): Promise<Brand> {
    return apiRequest<Brand>(`/brands/${brandId}`, { method: "PATCH", body: payload });
  },

  remove(brandId: string): Promise<void> {
    return apiRequest<void>(`/brands/${brandId}`, { method: "DELETE" });
  },
};
