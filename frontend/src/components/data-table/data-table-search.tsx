"use client";

import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type DataTableSearchProps = {
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  ariaLabel: string;
  className?: string;
};

/** Search box with the leading glyph used across every list screen. */
function DataTableSearch({
  value,
  onValueChange,
  placeholder,
  ariaLabel,
  className,
}: DataTableSearchProps) {
  return (
    <div className={cn("relative w-full max-w-xs", className)}>
      <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
      <Input
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        className="pl-8"
      />
    </div>
  );
}

export { DataTableSearch };
