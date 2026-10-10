"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellOff, CheckCheck, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { useCan } from "@/components/auth/can";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { NotificationRow } from "@/components/notifications/notification-item";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { describeError } from "@/lib/api/client";
import { notificationsApi, type NotificationType } from "@/lib/api/notifications";

const PAGE_SIZE = 20;

const TYPE_FILTERS: { value: NotificationType | "all"; label: string }[] = [
  { value: "all", label: "All types" },
  { value: "low_stock", label: "Low stock" },
  { value: "out_of_stock", label: "Out of stock" },
  { value: "customer_due", label: "Customer due" },
  { value: "supplier_due", label: "Supplier due" },
  { value: "new_sale", label: "New sale" },
  { value: "refund", label: "Refund" },
  { value: "system", label: "System" },
];

export function NotificationsClient() {
  const canRead = useCan("notifications:read");
  const queryClient = useQueryClient();

  const [type, setType] = React.useState<NotificationType | "all">("all");
  const [unreadOnly, setUnreadOnly] = React.useState(false);
  const [page, setPage] = React.useState(1);

  const params = {
    page,
    page_size: PAGE_SIZE,
    unread: unreadOnly ? true : undefined,
    type: type === "all" ? undefined : type,
  };

  const query = useQuery({
    queryKey: ["notifications", "list", params],
    queryFn: () => notificationsApi.list(params),
    enabled: canRead,
  });

  const refresh = React.useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }, [queryClient]);

  const markOne = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: refresh,
    onError: (cause) => toast.error(describeError(cause)),
  });

  const markAll = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      refresh();
      toast.success("All notifications marked as read");
    },
    onError: (cause) => toast.error(describeError(cause)),
  });

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader
          title="Notifications"
          description="Alerts about stock, sales and account balances."
        />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to notifications"
              description="This screen requires the notifications:read permission."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const pages = query.data?.pages ?? 1;
  const hasUnread = items.some((item) => item.read_at === null);

  return (
    <PageContainer>
      <PageHeader
        title="Notifications"
        description="Alerts about stock levels, sales, refunds and account balances."
        actions={
          <Button
            variant="outline"
            disabled={markAll.isPending || !hasUnread}
            onClick={() => markAll.mutate()}
          >
            <CheckCheck className="size-4" />
            Mark all as read
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={type}
          onValueChange={(value) => {
            setType(value as NotificationType | "all");
            setPage(1);
          }}
        >
          <SelectTrigger className="w-44" aria-label="Filter by type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TYPE_FILTERS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant={unreadOnly ? "default" : "outline"}
          size="sm"
          aria-pressed={unreadOnly}
          onClick={() => {
            setUnreadOnly((current) => !current);
            setPage(1);
          }}
        >
          Unread only
        </Button>

        <span className="text-muted-foreground ml-auto text-xs">{total} total</span>
      </div>

      <Card className="overflow-hidden">
        {query.isPending ? (
          <div className="flex flex-col gap-2 p-3">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-14 w-full" />
            ))}
          </div>
        ) : query.isError ? (
          <CardContent>
            <ErrorState
              title="Could not load notifications"
              description={describeError(query.error)}
              action={
                <Button variant="outline" onClick={() => void query.refetch()}>
                  Try again
                </Button>
              }
            />
          </CardContent>
        ) : items.length === 0 ? (
          <EmptyState
            icon={BellOff}
            title="Nothing here"
            description={
              unreadOnly
                ? "You have no unread notifications."
                : "No notifications match this filter."
            }
          />
        ) : (
          <ul className="divide-y">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex items-center gap-2 pr-2 transition-colors hover:bg-muted/40"
              >
                <NotificationRow notification={item} className="flex-1" />
                {item.read_at === null ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0 text-xs"
                    disabled={markOne.isPending}
                    onClick={() => markOne.mutate(item.id)}
                  >
                    Mark read
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {pages > 1 ? (
        <div className="flex items-center justify-between gap-3">
          <span className="text-muted-foreground text-xs">
            Page {page} of {pages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pages}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </PageContainer>
  );
}
