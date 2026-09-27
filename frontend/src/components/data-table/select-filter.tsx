"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export type SelectFilterOption = {
  value: string;
  label: string;
};

type SelectFilterProps = {
  value: string;
  onValueChange: (value: string) => void;
  options: SelectFilterOption[];
  ariaLabel: string;
  className?: string;
};

/** Compact labelled dropdown used for status/parent filters on list screens. */
function SelectFilter({
  value,
  onValueChange,
  options,
  ariaLabel,
  className,
}: SelectFilterProps) {
  return (
    <Select value={value} onValueChange={onValueChange}>
      <SelectTrigger className={cn("w-full sm:w-48", className)} aria-label={ariaLabel}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export { SelectFilter };
