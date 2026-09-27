"use client";

import * as React from "react";
import { Eye, EyeOff } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/**
 * Password field with a visibility toggle.
 *
 * `ref` and the rest of the props (including `onChange` / `onBlur` from
 * react-hook-form's `register`) are forwarded straight to the underlying input.
 */
function PasswordInput({ className, ...props }: React.ComponentProps<"input">) {
  const [visible, setVisible] = React.useState(false);

  return (
    <div className="relative">
      <Input
        type={visible ? "text" : "password"}
        className={cn("pr-10", className)}
        {...props}
      />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
        className={cn(
          "text-muted-foreground hover:text-foreground absolute inset-y-0 right-0 flex w-9 items-center justify-center rounded-r-md",
          "outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/60",
        )}
      >
        {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  );
}

export { PasswordInput };
