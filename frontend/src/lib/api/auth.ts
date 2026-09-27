import { apiRequest } from "@/lib/api/client";

export type RoleSummary = {
  id: string;
  name: string;
  description: string | null;
  is_system?: boolean;
};

export type BranchSummary = {
  id: string;
  name: string;
  code: string;
};

/** Mirrors the backend `UserRead` schema. Never carries credential material. */
export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at: string | null;
  branch_id: string | null;
  branch: BranchSummary | null;
  roles: RoleSummary[];
  permissions: string[];
  created_at: string;
  updated_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
};

export type MessageResponse = {
  message: string;
};

export const authApi = {
  /** Credentials go in the body; the refresh token comes back as a cookie. */
  login(email: string, password: string): Promise<TokenResponse> {
    return apiRequest<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
      retryOn401: false,
    });
  },

  logout(): Promise<MessageResponse> {
    return apiRequest<MessageResponse>("/auth/logout", {
      method: "POST",
      retryOn401: false,
    });
  },

  me(): Promise<AuthUser> {
    return apiRequest<AuthUser>("/auth/me");
  },

  /** Always resolves with the same generic message, whether or not the account exists. */
  forgotPassword(email: string): Promise<MessageResponse> {
    return apiRequest<MessageResponse>("/auth/forgot-password", {
      method: "POST",
      body: { email },
      auth: false,
      retryOn401: false,
    });
  },

  resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
    return apiRequest<MessageResponse>("/auth/reset-password", {
      method: "POST",
      body: { token, new_password: newPassword },
      auth: false,
      retryOn401: false,
    });
  },

  changePassword(currentPassword: string, newPassword: string): Promise<MessageResponse> {
    return apiRequest<MessageResponse>("/auth/change-password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
      retryOn401: false,
    });
  },
};
