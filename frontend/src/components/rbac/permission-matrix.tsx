"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import type { Permission } from "@/lib/api/rbac";
import { groupPermissionsByResource, humanizeResource } from "@/lib/auth/permissions";
import { cn } from "@/lib/utils";

type PermissionMatrixProps = {
  /** The full catalog to render. */
  permissions: readonly Permission[];
  /** Selected permission codes. */
  value: readonly string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
  className?: string;
};

/**
 * The permission matrix: one row per resource, one toggle per action.
 *
 * Every cell is a real permission code (`resource:action`) rather than a
 * cosmetic flag, so what the administrator ticks is exactly what the API checks.
 */
function PermissionMatrix({
  permissions,
  value,
  onChange,
  disabled = false,
  className,
}: PermissionMatrixProps) {
  const selected = React.useMemo(() => new Set(value), [value]);
  const groups = React.useMemo(() => groupPermissionsByResource(permissions), [permissions]);

  const toggle = React.useCallback(
    (code: string, next: boolean) => {
      const draft = new Set(selected);
      if (next) draft.add(code);
      else draft.delete(code);
      onChange([...draft]);
    },
    [onChange, selected],
  );

  const toggleGroup = React.useCallback(
    (codes: readonly string[], next: boolean) => {
      const draft = new Set(selected);
      for (const code of codes) {
        if (next) draft.add(code);
        else draft.delete(code);
      }
      onChange([...draft]);
    },
    [onChange, selected],
  );

  if (groups.length === 0) {
    return <p className="text-muted-foreground text-sm">The permission catalog is empty.</p>;
  }

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {groups.map((group) => {
        const codes = group.items.map((permission) => permission.code);
        const granted = codes.filter((code) => selected.has(code)).length;
        const allGranted = granted === codes.length;
        const someGranted = granted > 0 && !allGranted;

        return (
          <div key={group.resource} className="overflow-hidden rounded-md border">
            <div className="bg-muted/40 flex items-center justify-between gap-3 border-b px-3 py-2">
              <label className="flex items-center gap-2.5">
                <Checkbox
                  checked={allGranted ? true : someGranted ? "indeterminate" : false}
                  onCheckedChange={(state) => toggleGroup(codes, state === true)}
                  disabled={disabled}
                  aria-label={`Toggle every ${group.label} permission`}
                />
                <span className="text-sm font-medium">{group.label}</span>
                <code className="text-muted-foreground font-mono text-xs">{group.resource}</code>
              </label>
              <Badge variant={granted > 0 ? "default" : "outline"}>
                {granted}/{codes.length}
              </Badge>
            </div>

            <div className="grid gap-1 p-2 sm:grid-cols-2 xl:grid-cols-3">
              {group.items.map((permission) => (
                <label
                  key={permission.code}
                  className={cn(
                    "hover:bg-accent/60 flex cursor-pointer items-start gap-2.5 rounded-md px-2 py-1.5 transition-colors",
                    disabled && "cursor-not-allowed opacity-60",
                  )}
                >
                  <Checkbox
                    className="mt-0.5"
                    checked={selected.has(permission.code)}
                    onCheckedChange={(state) => toggle(permission.code, state === true)}
                    disabled={disabled}
                  />
                  <span className="flex min-w-0 flex-col">
                    <span className="text-sm leading-tight">
                      {humanizeResource(permission.action)}
                    </span>
                    <span className="text-muted-foreground font-mono text-[0.6875rem] leading-tight">
                      {permission.code}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export { PermissionMatrix };
