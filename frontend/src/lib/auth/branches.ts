import type { AuthUser, BranchSummary } from "@/lib/api/auth";
import type { SelectFilterOption } from "@/components/data-table/select-filter";

/**
 * Client-side branch helpers.
 *
 * The server is the authority on which branches a user may touch (see
 * `app/services/branch_access.py`); these functions only shape the UI — which
 * branches to offer and what to default to. A restricted user is offered only
 * their assigned branches, and "All branches" appears only for an account that
 * actually holds the `branches:all` grant.
 */
export const ALL_BRANCHES = "all";

/** True when the account may read and act on every branch. */
export function canSeeAllBranches(user: AuthUser | null | undefined): boolean {
  return user?.all_branches ?? false;
}

/** The branches the account may use, in the order the API returns them. */
export function myBranches(user: AuthUser | null | undefined): BranchSummary[] {
  return user?.branches ?? [];
}

/** Dropdown options for the account's branches. */
export function myBranchOptions(
  user: AuthUser | null | undefined,
): SelectFilterOption[] {
  return myBranches(user).map((branch) => ({ value: branch.id, label: branch.name }));
}

/**
 * The branch a screen should start on: "all" for an account that may see every
 * branch, else their primary branch, else the first branch they are assigned.
 */
export function defaultBranchId(user: AuthUser | null | undefined): string {
  if (canSeeAllBranches(user)) return ALL_BRANCHES;
  return user?.branch_id ?? myBranches(user)[0]?.id ?? ALL_BRANCHES;
}
