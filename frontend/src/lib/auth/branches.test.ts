import { describe, expect, it } from "vitest";

import type { AuthUser } from "@/lib/api/auth";
import {
  ALL_BRANCHES,
  canSeeAllBranches,
  defaultBranchId,
  myBranchOptions,
  myBranches,
} from "./branches";

function user(overrides: Partial<AuthUser>): AuthUser {
  return {
    id: "u1",
    email: "u@example.com",
    full_name: "User",
    phone: null,
    is_active: true,
    is_superuser: false,
    last_login_at: null,
    branch_id: null,
    branch: null,
    branches: [],
    all_branches: false,
    roles: [],
    permissions: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const main = { id: "b-main", name: "Main Branch", code: "MAIN" };
const other = { id: "b-other", name: "Other Branch", code: "OTHER" };

describe("branch helpers", () => {
  it("reports all-branch access only for the grant holder", () => {
    expect(canSeeAllBranches(user({ all_branches: true }))).toBe(true);
    expect(canSeeAllBranches(user({ all_branches: false }))).toBe(false);
    expect(canSeeAllBranches(null)).toBe(false);
  });

  it("lists the account's branches as options", () => {
    const scoped = user({ branches: [main, other] });
    expect(myBranches(scoped)).toHaveLength(2);
    expect(myBranchOptions(scoped)).toEqual([
      { value: "b-main", label: "Main Branch" },
      { value: "b-other", label: "Other Branch" },
    ]);
  });

  it("defaults an administrator to all branches", () => {
    expect(defaultBranchId(user({ all_branches: true, branches: [] }))).toBe(ALL_BRANCHES);
  });

  it("defaults a scoped user to their primary branch", () => {
    const scoped = user({ branch_id: "b-other", branches: [main, other] });
    expect(defaultBranchId(scoped)).toBe("b-other");
  });

  it("falls back to the first assigned branch when there is no primary", () => {
    const scoped = user({ branch_id: null, branches: [main, other] });
    expect(defaultBranchId(scoped)).toBe("b-main");
  });

  it("falls back to all when nothing is known", () => {
    expect(defaultBranchId(null)).toBe(ALL_BRANCHES);
  });
});
