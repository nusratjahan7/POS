"use client";

import { ChevronDown, LogOut, Settings, User } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/**
 * Session surface. There is no authentication module yet, so the menu states
 * that plainly instead of faking an identity.
 */
function UserMenu() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Account menu"
          className="hover:bg-accent focus-visible:ring-ring/60 flex items-center gap-2 rounded-md p-1 pr-1.5 transition-colors outline-none focus-visible:ring-2"
        >
          <span className="bg-primary/10 text-primary flex size-7 shrink-0 items-center justify-center rounded-full">
            <User className="size-3.5" aria-hidden />
          </span>
          <span className="hidden flex-col items-start sm:flex">
            <span className="text-xs leading-none font-medium">Not signed in</span>
            <span className="text-muted-foreground mt-1 text-[0.6875rem] leading-none">
              No active session
            </span>
          </span>
          <ChevronDown className="text-muted-foreground size-3.5 shrink-0" aria-hidden />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel>Account</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled>
          <User className="size-4" />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem disabled>
          <Settings className="size-4" />
          Preferences
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" disabled>
          <LogOut className="size-4" />
          Sign out
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <p className="text-muted-foreground px-2 py-1.5 text-xs leading-relaxed">
          Authentication ships in the next module.
        </p>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export { UserMenu };
