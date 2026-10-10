"use client";

import { PickedDateRange, SalesDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { BranchFilter } from "@/components/branch/branch-filter";
import { SelectFilter, type SelectFilterOption } from "@/components/data-table/select-filter";
import { ALL_BRANCHES } from "@/lib/auth/branches";
import type { ReportPreset } from "@/lib/api/reports";

export { ALL_BRANCHES };

const PRESET_OPTIONS: SelectFilterOption[] = [
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "this_week", label: "This week" },
  { value: "this_month", label: "This month" },
  { value: "this_year", label: "This year" },
  { value: "custom", label: "Custom range" },
];

/** The report toolbar: a date preset (with a custom range) and a branch filter. */
export function ReportFilters({
  preset,
  onPresetChange,
  range,
  onRangeChange,
  branchId,
  onBranchChange,
}: {
  preset: ReportPreset;
  onPresetChange: (preset: ReportPreset) => void;
  range: PickedDateRange | null;
  onRangeChange: (range: PickedDateRange | null) => void;
  branchId: string;
  onBranchChange: (branchId: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
      <SelectFilter
        value={preset}
        onValueChange={(value) => onPresetChange(value as ReportPreset)}
        options={PRESET_OPTIONS}
        ariaLabel="Date range"
        className="sm:w-44"
      />
      {preset === "custom" ? <SalesDateRange value={range} onChange={onRangeChange} /> : null}
      <BranchFilter value={branchId} onValueChange={onBranchChange} className="sm:w-52" />
    </div>
  );
}
