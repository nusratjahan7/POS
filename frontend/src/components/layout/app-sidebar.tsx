"use client";

import * as React from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { Brand } from "@/components/layout/brand";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/** Desktop navigation rail. Collapses to icons only; hidden below `lg`. */
function AppSidebar() {
  const [collapsed, setCollapsed] = React.useState(false);

  return (
    <aside
      data-collapsed={collapsed}
      className={cn(
        "bg-sidebar text-sidebar-foreground border-sidebar-border sticky top-0 hidden h-svh shrink-0 flex-col border-r lg:flex",
        "transition-[width] duration-200 ease-out",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div
        className={cn(
          "border-sidebar-border flex h-14 shrink-0 items-center border-b",
          collapsed ? "group/rail relative justify-center px-2" : "justify-between pl-4 pr-2",
        )}
      >
        <Brand collapsed={collapsed} />
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setCollapsed((value) => !value)}
              aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
              className={cn(
                "text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                // Collapsed, the rail only fits the glyph: the toggle overlays it
                // and fades in on hover or keyboard focus.
                collapsed &&
                  "bg-sidebar text-sidebar-foreground absolute inset-0 m-auto opacity-0 transition-opacity group-hover/rail:opacity-100 group-focus-within/rail:opacity-100",
              )}
            >
              {collapsed ? (
                <PanelLeftOpen className="size-4" />
              ) : (
                <PanelLeftClose className="size-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {collapsed ? "Expand navigation" : "Collapse navigation"}
          </TooltipContent>
        </Tooltip>
      </div>

      <SidebarNav collapsed={collapsed} />

      <div
        className={cn(
          "border-sidebar-border flex shrink-0 items-center border-t",
          collapsed ? "justify-center p-3" : "justify-between px-4 py-3",
        )}
      >
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="bg-success size-1.5 rounded-full" aria-hidden />
            </TooltipTrigger>
            <TooltipContent side="right">API v1 · development</TooltipContent>
          </Tooltip>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <span className="bg-success size-1.5 rounded-full" aria-hidden />
              <span className="text-sidebar-foreground/60 text-xs">API v1</span>
            </div>
            <Badge variant="outline" className="border-sidebar-border text-sidebar-foreground/60">
              Development
            </Badge>
          </>
        )}
      </div>
    </aside>
  );
}

export { AppSidebar };
