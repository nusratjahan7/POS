"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { ApiError, describeError } from "@/lib/api/client";
import { registersApi, type Register } from "@/lib/api/settings";
import type { BranchOption } from "@/lib/api/rbac";
import { cn } from "@/lib/utils";

const AMOUNT = /^\d+(\.\d{1,2})?$/;

const schema = z.object({
  name: z.string().min(1, "Name is required.").max(120, "Use at most 120 characters."),
  branch_id: z.string().uuid("Select a branch."),
  default_opening_balance: z
    .string()
    .refine((value) => value === "" || AMOUNT.test(value), "Enter an amount like 100 or 100.50."),
});

type FormValues = z.infer<typeof schema>;

type RegisterFormDialogProps = {
  /** `null` creates a new register. */
  register: Register | null;
  branches: readonly BranchOption[];
  /** Preselected branch for a new register (the list filter, when set). */
  defaultBranchId?: string;
  onClose: () => void;
  onSaved: () => void;
};

/** Mounted fresh for each open (the caller supplies a `key`). */
export function RegisterFormDialog({
  register,
  branches,
  defaultBranchId,
  onClose,
  onSaved,
}: RegisterFormDialogProps) {
  const [branchId, setBranchId] = React.useState(
    register?.branch_id ?? defaultBranchId ?? branches[0]?.id ?? "",
  );
  const [isActive, setIsActive] = React.useState(register?.is_active ?? true);
  const [requireOpening, setRequireOpening] = React.useState(
    register?.require_opening_balance ?? false,
  );
  const [allowOverride, setAllowOverride] = React.useState(
    register?.allow_opening_balance_override ?? true,
  );
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register: field,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: register?.name ?? "",
      branch_id: register?.branch_id ?? defaultBranchId ?? branches[0]?.id ?? "",
      default_opening_balance: register?.default_opening_balance ?? "0",
    },
  });

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const amount = values.default_opening_balance.trim();
    const payload = {
      name: values.name.trim(),
      branch_id: branchId,
      is_active: isActive,
      default_opening_balance: amount === "" ? "0" : Number(amount).toFixed(2),
      require_opening_balance: requireOpening,
      allow_opening_balance_override: allowOverride,
    };

    try {
      if (register) {
        await registersApi.update(register.id, payload);
        toast.success(`Updated ${payload.name}`);
      } else {
        await registersApi.create(payload);
        toast.success(`Created ${payload.name}`);
      }
      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError) {
        for (const [fieldName, message] of Object.entries(cause.fieldErrors)) {
          if (fieldName === "name" || fieldName === "branch_id") {
            setError(fieldName, { message });
          }
        }
      }
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !isSubmitting && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{register ? `Edit ${register.name}` : "New register"}</DialogTitle>
          <DialogDescription>
            A register is a till inside a branch. Opening-balance rules apply when a shift starts.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the register</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name" htmlFor="register-name" error={errors.name?.message}>
              <Input
                id="register-name"
                placeholder="Front counter"
                autoComplete="off"
                {...field("name")}
              />
            </Field>

            <Field label="Branch" htmlFor="register-branch" error={errors.branch_id?.message}>
              <Select value={branchId} onValueChange={setBranchId} disabled={branches.length === 0}>
                <SelectTrigger id="register-branch" className="w-full">
                  <SelectValue placeholder="Select branch" />
                </SelectTrigger>
                <SelectContent>
                  {branches.map((branch) => (
                    <SelectItem key={branch.id} value={branch.id}>
                      {branch.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>

          <div className="flex flex-col gap-4 rounded-md border p-3">
            <p className="text-sm font-medium">Opening balance</p>

            <Field
              label="Default opening balance"
              htmlFor="register-opening-balance"
              error={errors.default_opening_balance?.message}
              hint="The cash a shift is expected to start with."
            >
              <Input
                id="register-opening-balance"
                inputMode="decimal"
                placeholder="0.00"
                {...field("default_opening_balance")}
              />
            </Field>

            <label
              className={cn(
                "flex cursor-pointer items-center gap-2.5",
                isSubmitting && "cursor-not-allowed opacity-60",
              )}
            >
              <Checkbox
                checked={requireOpening}
                disabled={isSubmitting}
                onCheckedChange={(state) => setRequireOpening(state === true)}
              />
              <span className="flex flex-col">
                <span className="text-sm font-medium">Require an opening balance</span>
                <span className="text-muted-foreground text-xs">
                  A cashier must record the float before the first sale.
                </span>
              </span>
            </label>

            <label
              className={cn(
                "flex cursor-pointer items-center gap-2.5",
                (!requireOpening || isSubmitting) && "cursor-not-allowed opacity-60",
              )}
            >
              <Checkbox
                checked={allowOverride}
                disabled={!requireOpening || isSubmitting}
                onCheckedChange={(state) => setAllowOverride(state === true)}
              />
              <span className="flex flex-col">
                <span className="text-sm font-medium">Let cashiers change the amount</span>
                <span className="text-muted-foreground text-xs">
                  When off, the default above is locked for every shift.
                </span>
              </span>
            </label>
          </div>

          <label className={cn("flex w-fit cursor-pointer items-center gap-2.5", isSubmitting && "opacity-60")}>
            <Checkbox
              checked={isActive}
              disabled={isSubmitting}
              onCheckedChange={(state) => setIsActive(state === true)}
            />
            <span className="text-sm">This register is active</span>
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || branches.length === 0}>
              {isSubmitting ? <Spinner /> : null}
              {register ? "Save changes" : "Create register"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
