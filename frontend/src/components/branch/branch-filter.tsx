"use client";

import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/components/auth/auth-provider";
import { SelectFilter, type SelectFilterOption } from "@/components/data-table/select-filter";
import { branchesApi } from "@/lib/api/rbac";
import { ALL_BRANCHES, canSeeAllBranches } from "@/lib/auth/branches";

type BranchFilterProps = {
  value: string;
  onValueChange: (value: string) => void;
  /** Shown as the first option for accounts that may see every branch. */
  allLabel?: string;
  className?: string;
  ariaLabel?: string;
};

/**
 * The one branch selector, reused by every management screen.
 *
 * Its options come from `/branches/options`, which the server already scopes to
 * the caller: an administrator sees every branch, a restricted user only their
 * assigned ones. "All branches" is appended only for an account holding the
 * `branches:all` grant, and a user with a single branch (and no "all") gets no
 * control at all — there is nothing to choose.
 *
 * Selection is cosmetic: the API enforces the same scope, so hiding or faking
 * this control cannot grant access.
 */
export function BranchFilter({
  value,
  onValueChange,
  allLabel = "All branches",
  className,
  ariaLabel = "Filter by branch",
}: BranchFilterProps) {
  const { user } = useAuth();
  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
  });

  const options: SelectFilterOption[] = [
    ...(canSeeAllBranches(user) ? [{ value: ALL_BRANCHES, label: allLabel }] : []),
    ...(branchesQuery.data ?? []).map((branch) => ({ value: branch.id, label: branch.name })),
  ];

  // One option or fewer means there is nothing to switch between.
  if (options.length <= 1) return null;

  return (
    <SelectFilter
      value={value}
      onValueChange={onValueChange}
      options={options}
      ariaLabel={ariaLabel}
      className={className}
    />
  );
}
