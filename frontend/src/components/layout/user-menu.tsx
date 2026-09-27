"use client";

import Link from "next/link";
import { ChevronDown, KeyRound, LogOut, User } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { initials } from "@/lib/format";

/** The signed-in account: identity, password change, and sign-out. */
function UserMenu() {
  const { user, logout } = useAuth();

  const name = user?.full_name ?? "Account";
  const email = user?.email ?? "";
  const role = user?.is_superuser ? "Superuser" : (user?.roles[0]?.name ?? "Staff");

  async function handleSignOut() {
    await logout();
    // `RequireAuth` redirects to /login once the session clears.
    toast.success("Signed out");
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Account menu"
          className="hover:bg-accent focus-visible:ring-ring/60 flex items-center gap-2 rounded-md p-1 pr-1.5 transition-colors outline-none focus-visible:ring-2"
        >
          <span className="bg-primary/10 text-primary flex size-7 shrink-0 items-center justify-center rounded-full text-[0.6875rem] font-semibold">
            {initials(name) || <User className="size-3.5" aria-hidden />}
          </span>
          <span className="hidden min-w-0 flex-col items-start sm:flex">
            <span className="max-w-[9rem] truncate text-xs leading-none font-medium">{name}</span>
            <span className="text-muted-foreground mt-1 max-w-[9rem] truncate text-[0.6875rem] leading-none">
              {email}
            </span>
          </span>
          <ChevronDown className="text-muted-foreground size-3.5 shrink-0" aria-hidden />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="flex flex-col gap-1.5">
          <span className="text-foreground text-sm leading-none font-medium">{name}</span>
          <span className="text-muted-foreground text-xs leading-none font-normal">{email}</span>
          <Badge variant="outline" className="mt-0.5 w-fit">
            {role}
          </Badge>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        <DropdownMenuItem asChild>
          <Link href="/change-password">
            <KeyRound className="size-4" />
            Change password
          </Link>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem variant="destructive" onSelect={handleSignOut}>
          <LogOut className="size-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export { UserMenu };
