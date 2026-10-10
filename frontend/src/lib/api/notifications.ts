import { apiRequest } from "@/lib/api/client";
import { withQuery, type Page } from "@/lib/api/rbac";

export type NotificationType =
  | "low_stock"
  | "out_of_stock"
  | "customer_due"
  | "supplier_due"
  | "new_sale"
  | "refund"
  | "system";

export type NotificationSeverity = "info" | "warning" | "critical";

/** One in-app notification addressed to the signed-in user. */
export type AppNotification = {
  id: string;
  type: NotificationType;
  severity: NotificationSeverity;
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_id: string | null;
  data: Record<string, unknown> | null;
  read_at: string | null;
  created_at: string;
};

export type NotificationListParams = {
  page?: number;
  page_size?: number;
  unread?: boolean;
  type?: NotificationType;
};

export const notificationsApi = {
  list(params: NotificationListParams = {}): Promise<Page<AppNotification>> {
    return apiRequest<Page<AppNotification>>(
      withQuery("/notifications", { page_size: 20, ...params }),
    );
  },

  /** The number on the bell. */
  unreadCount(): Promise<{ unread: number }> {
    return apiRequest<{ unread: number }>("/notifications/unread-count");
  },

  markRead(notificationId: string): Promise<AppNotification> {
    return apiRequest<AppNotification>(`/notifications/${notificationId}/read`, { method: "POST" });
  },

  markAllRead(): Promise<{ unread: number }> {
    return apiRequest<{ unread: number }>("/notifications/read-all", { method: "POST" });
  },
};
