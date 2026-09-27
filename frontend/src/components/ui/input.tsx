import * as React from "react";

import { cn } from "@/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "flex h-9 w-full min-w-0 rounded-md border border-input bg-card px-3 py-1 text-sm shadow-xs",
        "transition-[color,box-shadow,border-color] duration-150 outline-none",
        "placeholder:text-muted-foreground/70",
        "file:mr-3 file:h-7 file:rounded-sm file:border-0 file:bg-secondary file:px-2 file:text-xs file:font-medium file:text-secondary-foreground",
        "focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40",
        "aria-invalid:border-destructive aria-invalid:ring-destructive/25",
        "disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
