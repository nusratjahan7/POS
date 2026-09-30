"use client";

import { useQuery } from "@tanstack/react-query";

import type { PickedDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { SalesDateRange } from "@/app/(dashboard)/sales/sales-date-range";
import { SelectFilter, type SelectFilterOption } from "@/components/data-table/select-filter";
import { branchesApi } from "@/lib/api/rbac";
import type { ReportPreset } from "@/lib/api/reports";

export const ALL_BRANCHES = "all";

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
  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
  });

  const branchOptions: SelectFilterOption[] = [
    { value: ALL_BRANCHES, label: "All branches" },
    ...(branchesQuery.data ?? []).map((branch) => ({ value: branch.id, label: branch.name })),
  ];

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
      <SelectFilter
        value={branchId}
        onValueChange={onBranchChange}
        options={branchOptions}
        ariaLabel="Filter by branch"
        className="sm:w-52"
      />
    </div>
  );
}
