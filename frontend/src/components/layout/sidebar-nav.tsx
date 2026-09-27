"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/auth-provider";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { hasPermission } from "@/lib/auth/permissions";
import { navGroups, type NavItem } from "@/lib/nav";
import { cn } from "@/lib/utils";

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

const itemBase =
  "group/nav relative flex items-center rounded-md text-sm font-medium outline-none transition-colors duration-150 " +
  "focus-visible:ring-2 focus-visible:ring-sidebar-ring/60";

function NavLink({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const pathname = usePathname();
  const active = isActive(pathname, item.href);
  const Icon = item.icon;

  if (item.status === "planned") {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-disabled
            className={cn(
              itemBase,
              collapsed ? "size-9 justify-center" : "w-full gap-2.5 px-2.5 py-2",
              "text-sidebar-foreground/45 cursor-not-allowed",
            )}
          >
            <Icon className="size-4 shrink-0" aria-hidden />
            {collapsed ? null : (
              <>
                <span className="truncate">{item.title}</span>
                <span className="border-sidebar-border text-sidebar-foreground/50 ml-auto rounded-full border px-1.5 py-px text-[0.625rem] font-medium tracking-wide uppercase">
                  Soon
                </span>
              </>
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">{item.title} — ships in a later module</TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        itemBase,
        collapsed ? "size-9 justify-center" : "w-full gap-2.5 px-2.5 py-2",
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground/70 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
        !collapsed &&
          active &&
          "before:bg-sidebar-primary before:absolute before:top-1/2 before:left-0 before:h-4 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full",
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      {collapsed ? (
        <span className="sr-only">{item.title}</span>
      ) : (
        <span className="truncate">{item.title}</span>
      )}
    </Link>
  );
}

function SidebarNav({
  collapsed = false,
  onNavigate,
}: {
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const { user } = useAuth();

  // Each entry declares the permission it needs; groups that end up empty vanish.
  const visibleGroups = React.useMemo(
    () =>
      navGroups
        .map((group) => ({
          ...group,
          items: group.items.filter(
            (item) => !item.permission || hasPermission(user, item.permission),
          ),
        }))
        .filter((group) => group.items.length > 0),
    [user],
  );

  return (
    <nav
      aria-label="Primary"
      className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 py-4"
      onClick={onNavigate}
    >
      {visibleGroups.map((group) => (
        <div key={group.label} className="flex flex-col gap-1">
          {collapsed ? (
            <div className="bg-sidebar-border mx-auto mb-1.5 h-px w-6" aria-hidden />
          ) : (
            <p className="text-sidebar-foreground/45 px-2.5 pb-1 text-[0.6875rem] font-semibold tracking-wider uppercase">
              {group.label}
            </p>
          )}
          {group.items.map((item) => (
            <NavLink key={item.href} item={item} collapsed={collapsed} />
          ))}
        </div>
      ))}

      {visibleGroups.length === 0 ? (
        <p className="text-sidebar-foreground/50 px-2.5 text-xs">
          No modules are available for your role.
        </p>
      ) : null}
    </nav>
  );
}

export { SidebarNav };
