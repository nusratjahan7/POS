import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

/** One immutable entry in the security audit log. */
export type AuditLogEntry = {
  id: string;
  user_id: string | null;
  user_email: string | null;
  user_name: string | null;
  action: string;
  module: string;
  entity: string | null;
  entity_id: string | null;
  old_data: Record<string, unknown> | null;
  new_data: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
};

export type AuditLogParams = {
  page?: number;
  page_size?: number;
  module?: string;
  action?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
};

export const auditApi = {
  list(params: AuditLogParams = {}): Promise<Page<AuditLogEntry>> {
    return apiRequest<Page<AuditLogEntry>>(withQuery("/audit-logs", { page_size: 20, ...params }));
  },
};
