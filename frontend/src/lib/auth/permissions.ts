import type { AuthUser } from "@/lib/api/auth";

/** Superusers are granted every permission and report this sentinel instead of a list. */
export const WILDCARD_PERMISSION = "*";

/**
 * Client-side permission checks.
 *
 * These exist to shape the UI. They are NOT authorization — the API enforces
 * every permission server-side via `require_permissions`, so a user who
 * circumvents the UI still gets a 403.
 */
export function hasPermission(user: AuthUser | null | undefined, code: string): boolean {
  if (!user) return false;
  if (user.permissions.includes(WILDCARD_PERMISSION)) return true;
  return user.permissions.includes(code);
}

export function hasAnyPermission(
  user: AuthUser | null | undefined,
  codes: readonly string[],
): boolean {
  return codes.some((code) => hasPermission(user, code));
}

export function hasAllPermissions(
  user: AuthUser | null | undefined,
  codes: readonly string[],
): boolean {
  return codes.every((code) => hasPermission(user, code));
}

export function isSuperuser(user: AuthUser | null | undefined): boolean {
  return user?.permissions.includes(WILDCARD_PERMISSION) ?? false;
}

/** `"catalog"` -> `"Catalog"`, `"inventory"` -> `"Inventory"`. */
export function humanizeResource(resource: string): string {
  return resource
    .split(/[:_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export type GroupedPermissions<T> = {
  resource: string;
  label: string;
  items: T[];
};

/** Groups a flat permission catalog by resource, ready for a matrix layout. */
export function groupPermissionsByResource<T extends { resource: string; action: string }>(
  permissions: readonly T[],
): GroupedPermissions<T>[] {
  const groups = new Map<string, T[]>();

  for (const permission of permissions) {
    const bucket = groups.get(permission.resource);
    if (bucket) bucket.push(permission);
    else groups.set(permission.resource, [permission]);
  }

  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([resource, items]) => ({
      resource,
      label: humanizeResource(resource),
      items: [...items].sort((a, b) => a.action.localeCompare(b.action)),
    }));
}
