"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import { PasswordInput } from "@/components/ui/password-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { ApiError, describeError } from "@/lib/api/client";
import { usersApi, type BranchOption, type ManagedUser, type RoleSummary } from "@/lib/api/rbac";
import { emailSchema, passwordSchema } from "@/lib/auth/validation";
import { cn } from "@/lib/utils";

const UNASSIGNED = "unassigned";

/** The password policy applies only when creating; an edit leaves it untouched. */
function buildSchema(isEdit: boolean) {
  return z.object({
    email: emailSchema,
    full_name: z
      .string()
      .min(1, "Full name is required.")
      .max(160, "Use at most 160 characters."),
    phone: z.string().max(32, "Use at most 32 characters."),
    password: isEdit ? z.string() : passwordSchema,
  });
}

type FormValues = z.infer<ReturnType<typeof buildSchema>>;

type UserFormDialogProps = {
  /** `null` creates a new account. */
  user: ManagedUser | null;
  roles: readonly RoleSummary[];
  branches: readonly BranchOption[];
  onClose: () => void;
  onSaved: () => void;
};

/**
 * Mounted fresh for each open (the caller supplies a `key`), so initial state is
 * derived from props once and needs no synchronising effect.
 */
export function UserFormDialog({
  user,
  roles,
  branches,
  onClose,
  onSaved,
}: UserFormDialogProps) {
  const isEdit = user !== null;
  const schema = React.useMemo(() => buildSchema(isEdit), [isEdit]);

  const [roleIds, setRoleIds] = React.useState<string[]>(
    user ? user.roles.map((role) => role.id) : [],
  );
  const [branchId, setBranchId] = React.useState<string>(user?.branch?.id ?? UNASSIGNED);
  const [isActive, setIsActive] = React.useState(user?.is_active ?? true);
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: user?.email ?? "",
      full_name: user?.full_name ?? "",
      phone: user?.phone ?? "",
      password: "",
    },
  });

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const shared = {
      full_name: values.full_name.trim(),
      phone: values.phone.trim() || null,
      is_active: isActive,
      branch_id: branchId === UNASSIGNED ? null : branchId,
      role_ids: roleIds,
    };

    try {
      if (user) {
        await usersApi.update(user.id, shared);
        toast.success(`Updated ${shared.full_name}`);
      } else {
        await usersApi.create({ ...shared, email: values.email.trim(), password: values.password });
        toast.success(`Created ${shared.full_name}`, {
          description: `${roleIds.length} role${roleIds.length === 1 ? "" : "s"} assigned.`,
        });
      }

      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError) {
        for (const [field, message] of Object.entries(cause.fieldErrors)) {
          if (field === "email" || field === "full_name" || field === "phone") {
            setError(field, { message });
          }
        }
      }
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !isSubmitting && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{user ? `Edit ${user.full_name}` : "New user"}</DialogTitle>
          <DialogDescription>
            {user
              ? "Email addresses are immutable. Roles decide what this account can do."
              : "Roles decide what this account can do. An account with no roles can sign in but access nothing."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the account</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Email"
              htmlFor="user-email"
              error={errors.email?.message}
              hint={isEdit ? "Email cannot be changed." : undefined}
            >
              <Input
                id="user-email"
                type="email"
                autoComplete="off"
                disabled={isEdit}
                placeholder="name@example.com"
                {...register("email")}
              />
            </Field>

            <Field label="Full name" htmlFor="user-name" error={errors.full_name?.message}>
              <Input
                id="user-name"
                autoComplete="off"
                placeholder="Jane Doe"
                {...register("full_name")}
              />
            </Field>

            <Field label="Phone" htmlFor="user-phone" error={errors.phone?.message}>
              <Input id="user-phone" autoComplete="off" placeholder="Optional" {...register("phone")} />
            </Field>

            <Field label="Branch" htmlFor="user-branch">
              <Select value={branchId} onValueChange={setBranchId}>
                <SelectTrigger id="user-branch" className="w-full">
                  <SelectValue placeholder="Unassigned" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
                  {branches.map((branch) => (
                    <SelectItem key={branch.id} value={branch.id}>
                      {branch.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          {isEdit ? null : (
            <Field
              label="Initial password"
              htmlFor="user-password"
              error={errors.password?.message}
              hint="At least 8 characters, with a letter, a digit and a symbol. They can change it after signing in."
            >
              <PasswordInput
                id="user-password"
                autoComplete="new-password"
                placeholder="••••••••"
                {...register("password")}
              />
            </Field>
          )}

          <div className="flex flex-col gap-3">
            <p className="text-sm font-medium">Roles</p>
            <div className="grid gap-1.5 rounded-md border p-2 sm:grid-cols-2">
              {roles.length === 0 ? (
                <p className="text-muted-foreground p-2 text-sm">No roles are defined yet.</p>
              ) : (
                roles.map((role) => (
                  <label
                    key={role.id}
                    className={cn(
                      "hover:bg-accent/60 flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-2 transition-colors",
                      isSubmitting && "cursor-not-allowed opacity-60",
                    )}
                  >
                    <Checkbox
                      checked={roleIds.includes(role.id)}
                      disabled={isSubmitting}
                      onCheckedChange={(state) =>
                        setRoleIds((current) =>
                          state === true
                            ? [...current, role.id]
                            : current.filter((id) => id !== role.id),
                        )
                      }
                    />
                    <span className="text-sm">{role.name}</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <label className="flex w-fit cursor-pointer items-center gap-2.5">
            <Checkbox
              checked={isActive}
              disabled={isSubmitting}
              onCheckedChange={(state) => setIsActive(state === true)}
            />
            <span className="text-sm">Account is active</span>
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {user ? "Save changes" : "Create user"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
