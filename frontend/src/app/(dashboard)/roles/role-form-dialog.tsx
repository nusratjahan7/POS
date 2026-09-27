"use client";

import * as React from "react";
import { toast } from "sonner";

import { PermissionMatrix } from "@/components/rbac/permission-matrix";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { ApiError, describeError } from "@/lib/api/client";
import { rolesApi, type Permission, type Role } from "@/lib/api/rbac";

type RoleFormDialogProps = {
  /** `null` creates a new role. */
  role: Role | null;
  catalog: readonly Permission[];
  onClose: () => void;
  onSaved: () => void;
};

/**
 * Mounted fresh for each open (the caller supplies a `key`), so initial state is
 * derived from props once and needs no synchronising effect.
 */
export function RoleFormDialog({ role, catalog, onClose, onSaved }: RoleFormDialogProps) {
  const isSystem = role?.is_system ?? false;
  // The Administrator role is fully locked: nobody may change it.
  const isProtected = role?.name === "Administrator";

  const [name, setName] = React.useState(role?.name ?? "");
  const [description, setDescription] = React.useState(role?.description ?? "");
  const [codes, setCodes] = React.useState<string[]>(
    role ? role.permissions.map((permission) => permission.code) : [],
  );
  const [nameError, setNameError] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedName = name.trim();
    if (!isSystem && trimmedName.length === 0) {
      setNameError("Name is required.");
      return;
    }

    setSaving(true);
    setFormError(null);

    try {
      if (role) {
        await rolesApi.update(role.id, {
          // A system role cannot be renamed, so the name is omitted entirely.
          ...(isSystem ? {} : { name: trimmedName }),
          description: description.trim() || null,
          permission_codes: codes,
        });
        toast.success(`Updated ${trimmedName || role.name}`, {
          description: `${codes.length} permission${codes.length === 1 ? "" : "s"} granted.`,
        });
      } else {
        await rolesApi.create({
          name: trimmedName,
          description: description.trim() || null,
          permission_codes: codes,
        });
        toast.success(`Created ${trimmedName}`, {
          description: `${codes.length} permission${codes.length === 1 ? "" : "s"} granted.`,
        });
      }

      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError && cause.fieldErrors.name) {
        setNameError(cause.fieldErrors.name);
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !saving && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{role ? `Edit ${role.name}` : "New role"}</DialogTitle>
          <DialogDescription>
            {isProtected
              ? "The Administrator role is owned by the application and cannot be changed."
              : "Every tick grants one capability that the API enforces independently of this screen."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the role</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Name"
              htmlFor="role-name"
              error={nameError}
              hint={isSystem ? "System roles cannot be renamed." : undefined}
            >
              <Input
                id="role-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={isSystem}
                placeholder="Shift Supervisor"
                autoComplete="off"
              />
            </Field>

            <Field label="Description" htmlFor="role-description">
              <Input
                id="role-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="What this role is responsible for"
                autoComplete="off"
              />
            </Field>
          </div>

          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium">Permissions</p>
            <div className="max-h-[22rem] overflow-y-auto pr-1">
              <PermissionMatrix
                permissions={catalog}
                value={codes}
                onChange={setCodes}
                disabled={saving || isProtected}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || isProtected}>
              {saving ? <Spinner /> : null}
              {role ? "Save changes" : "Create role"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
