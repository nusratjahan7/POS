import { apiRequest } from "@/lib/api/client";

/** The shared collection envelope every list endpoint returns. */
export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type Permission = {
  id: string;
  code: string;
  resource: string;
  action: string;
  description: string | null;
};

export type RoleSummary = {
  id: string;
  name: string;
};

export type Role = {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: Permission[];
  created_at: string;
  updated_at: string;
};

export type BranchOption = {
  id: string;
  name: string;
  code: string;
};

/** Mirrors the backend `UserSummary` returned by the list endpoint. */
export type ManagedUser = {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at: string | null;
  branch: BranchOption | null;
  roles: RoleSummary[];
  created_at: string;
};

export type RolePayload = {
  name: string;
  description?: string | null;
  permission_codes: string[];
};

export type UserPayload = {
  email?: string;
  full_name?: string;
  phone?: string | null;
  password?: string;
  is_active?: boolean;
  branch_id?: string | null;
  role_ids?: string[];
};

type QueryValue = string | number | boolean | undefined;

function withQuery(path: string, params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `${path}?${encoded}` : path;
}

export const permissionsApi = {
  /** The full granular catalog, used to render the permission matrix. */
  list(): Promise<Permission[]> {
    return apiRequest<Permission[]>("/permissions");
  },
};

export const rolesApi = {
  list(params: { page?: number; page_size?: number; search?: string } = {}): Promise<Page<Role>> {
    return apiRequest<Page<Role>>(withQuery("/roles", { page_size: 100, ...params }));
  },

  options(): Promise<RoleSummary[]> {
    return apiRequest<RoleSummary[]>("/roles/options");
  },

  create(payload: RolePayload): Promise<Role> {
    return apiRequest<Role>("/roles", { method: "POST", body: payload });
  },

  update(roleId: string, payload: Partial<RolePayload>): Promise<Role> {
    return apiRequest<Role>(`/roles/${roleId}`, { method: "PATCH", body: payload });
  },

  remove(roleId: string): Promise<void> {
    return apiRequest<void>(`/roles/${roleId}`, { method: "DELETE" });
  },
};

export const usersApi = {
  list(
    params: { page?: number; page_size?: number; search?: string; is_active?: boolean } = {},
  ): Promise<Page<ManagedUser>> {
    return apiRequest<Page<ManagedUser>>(withQuery("/users", { page_size: 20, ...params }));
  },

  create(payload: UserPayload): Promise<ManagedUser> {
    return apiRequest<ManagedUser>("/users", { method: "POST", body: payload });
  },

  update(userId: string, payload: UserPayload): Promise<ManagedUser> {
    return apiRequest<ManagedUser>(`/users/${userId}`, { method: "PATCH", body: payload });
  },

  deactivate(userId: string): Promise<void> {
    return apiRequest<void>(`/users/${userId}`, { method: "DELETE" });
  },

  setPassword(userId: string, password: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>(`/users/${userId}/password`, {
      method: "POST",
      body: { password },
    });
  },
};

export const branchesApi = {
  options(): Promise<BranchOption[]> {
    return apiRequest<BranchOption[]>("/branches/options");
  },
};
