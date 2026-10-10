import {
  AlertCircle,
  Bell,
  HandCoins,
  RotateCcw,
  ShoppingCart,
  TriangleAlert,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type {
  AppNotification,
  NotificationSeverity,
  NotificationType,
} from "@/lib/api/notifications";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export const NOTIFICATION_ICONS: Record<NotificationType, LucideIcon> = {
  low_stock: TriangleAlert,
  out_of_stock: AlertCircle,
  customer_due: Wallet,
  supplier_due: HandCoins,
  new_sale: ShoppingCart,
  refund: RotateCcw,
  system: Bell,
};

export const NOTIFICATION_LABELS: Record<NotificationType, string> = {
  low_stock: "Low stock",
  out_of_stock: "Out of stock",
  customer_due: "Customer due",
  supplier_due: "Supplier due",
  new_sale: "New sale",
  refund: "Refund",
  system: "System",
};

const SEVERITY_CHIP: Record<NotificationSeverity, string> = {
  info: "bg-info/12 text-info",
  warning: "bg-warning/15 text-warning-foreground",
  critical: "bg-destructive/10 text-destructive",
};

/** One notification row. Purely presentational — the caller owns interaction. */
export function NotificationRow({
  notification,
  className,
}: {
  notification: AppNotification;
  className?: string;
}) {
  const Icon = NOTIFICATION_ICONS[notification.type];
  const unread = notification.read_at === null;

  return (
    <div className={cn("flex items-start gap-3 px-3 py-2.5", className)}>
      <span
        aria-hidden
        className={cn(
          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md [&_svg]:size-4",
          SEVERITY_CHIP[notification.severity],
        )}
      >
        <Icon />
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className={cn("truncate text-sm", unread ? "font-medium" : "text-muted-foreground")}>
            {notification.title}
          </p>
          {unread ? (
            <span className="bg-primary size-1.5 shrink-0 rounded-full" aria-label="Unread" />
          ) : null}
        </div>

        {notification.body ? (
          <p className="text-muted-foreground mt-0.5 line-clamp-2 text-xs">{notification.body}</p>
        ) : null}

        <div className="mt-1.5 flex items-center gap-2">
          <Badge variant="outline" className="px-1.5 py-0 text-[0.625rem]">
            {NOTIFICATION_LABELS[notification.type]}
          </Badge>
          <span className="text-muted-foreground text-[0.6875rem]">
            {formatDateTime(notification.created_at)}
          </span>
        </div>
      </div>
    </div>
  );
}
