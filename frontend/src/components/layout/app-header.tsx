"use client";

import { Bell, Search } from "lucide-react";
import { toast } from "sonner";

import { CalculatorButton } from "@/components/calculator/calculator-button";
import { CalculatorPopup } from "@/components/calculator/calculator-popup";
import { Brand } from "@/components/layout/brand";
import { FullscreenToggle } from "@/components/layout/fullscreen-toggle";
import { MobileNav } from "@/components/layout/mobile-nav";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { UserMenu } from "@/components/layout/user-menu";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

function AppHeader() {
  return (
    <>
      <header className="bg-background/80 sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b px-3 backdrop-blur-md sm:px-4 lg:px-6">
        <MobileNav />
        <Brand className="lg:hidden" />

        <button
          type="button"
          onClick={() =>
            toast("Search is not available yet", {
              description: "It ships alongside the product and sales modules.",
            })
          }
          className="text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:ring-ring/60 hidden h-8 w-64 items-center gap-2 rounded-md border bg-card px-2.5 text-sm shadow-xs transition-colors outline-none focus-visible:ring-2 md:flex"
        >
          <Search className="size-3.5 shrink-0" aria-hidden />
          <span>Search</span>
          <kbd className="bg-muted text-muted-foreground ml-auto rounded border px-1.5 py-px font-sans text-[0.625rem] font-medium">
            ⌘K
          </kbd>
        </button>

        <div className="ml-auto flex items-center gap-1">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Notifications"
                onClick={() =>
                  toast.info("You're all caught up", {
                    description: "Notifications arrive with the sales module.",
                  })
                }
              >
                <Bell className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Notifications</TooltipContent>
          </Tooltip>

          <CalculatorButton />

          <FullscreenToggle />

          <ThemeToggle />

          <div className="bg-border mx-1 hidden h-5 w-px sm:block" aria-hidden />

          <UserMenu />
        </div>
      </header>

      <CalculatorPopup />
    </>
  );
}

export { AppHeader };
