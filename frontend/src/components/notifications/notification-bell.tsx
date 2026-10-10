"use client";

import * as React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { toast } from "sonner";

import { NotificationRow } from "@/components/notifications/notification-item";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { describeError } from "@/lib/api/client";
import { notificationsApi } from "@/lib/api/notifications";

const RECENT_LIMIT = 6;

/**
 * The header bell: an unread badge over a menu of the latest notifications.
 *
 * The count polls every 30s (the stack has no websockets); the list loads when
 * the menu opens.
 */
export function NotificationBell() {
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);

  const unreadQuery = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: notificationsApi.unreadCount,
    refetchInterval: 30_000,
  });

  const recentQuery = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () => notificationsApi.list({ page_size: RECENT_LIMIT }),
    enabled: open,
  });

  const refresh = React.useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }, [queryClient]);

  const markAll = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: refresh,
    onError: (cause) => toast.error(describeError(cause)),
  });

  const markOne = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: refresh,
    onError: (cause) => toast.error(describeError(cause)),
  });

  const unread = unreadQuery.data?.unread ?? 0;
  const items = recentQuery.data?.items ?? [];

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
        >
          <Bell className="size-4" />
          {unread > 0 ? (
            <span className="bg-destructive text-destructive-foreground absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[0.625rem] leading-none font-semibold tabular-nums">
              {unread > 9 ? "9+" : unread}
            </span>
          ) : null}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-[22rem] p-0">
        <div className="flex items-center justify-between gap-2 px-3 py-2">
          <span className="text-sm font-semibold">Notifications</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            disabled={unread === 0 || markAll.isPending}
            onClick={() => markAll.mutate()}
          >
            Mark all as read
          </Button>
        </div>

        <DropdownMenuSeparator className="mx-0 my-0" />

        <div className="max-h-80 overflow-y-auto py-1">
          {recentQuery.isPending ? (
            <div className="flex flex-col gap-2 p-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-12 w-full" />
              ))}
            </div>
          ) : recentQuery.isError ? (
            <p className="text-muted-foreground px-3 py-6 text-center text-sm">
              Could not load notifications.
            </p>
          ) : items.length === 0 ? (
            <p className="text-muted-foreground px-3 py-6 text-center text-sm">
              You&rsquo;re all caught up.
            </p>
          ) : (
            items.map((item) => (
              <DropdownMenuItem
                key={item.id}
                className="p-0"
                onSelect={(event) => {
                  event.preventDefault();
                  if (item.read_at === null) markOne.mutate(item.id);
                }}
              >
                <NotificationRow notification={item} className="w-full" />
              </DropdownMenuItem>
            ))
          )}
        </div>

        <DropdownMenuSeparator className="mx-0 my-0" />

        <DropdownMenuItem asChild>
          <Link href="/notifications" className="justify-center text-sm font-medium">
            View all notifications
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
