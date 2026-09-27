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
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, describeError } from "@/lib/api/client";
import { branchesApi, type Branch } from "@/lib/api/rbac";
import { cn } from "@/lib/utils";

const schema = z.object({
  name: z.string().min(1, "Name is required.").max(120, "Use at most 120 characters."),
  code: z
    .string()
    .min(1, "Code is required.")
    .max(20, "Use at most 20 characters.")
    .regex(/^[A-Za-z0-9_-]+$/, "Use letters, digits, hyphen or underscore only."),
  address: z.string().max(255, "Use at most 255 characters."),
  phone: z.string().max(32, "Use at most 32 characters."),
});

type FormValues = z.infer<typeof schema>;

type BranchFormDialogProps = {
  /** `null` creates a new branch. */
  branch: Branch | null;
  onClose: () => void;
  onSaved: () => void;
};

/** Mounted fresh for each open (the caller supplies a `key`). */
export function BranchFormDialog({ branch, onClose, onSaved }: BranchFormDialogProps) {
  const isEdit = branch !== null;
  const [isActive, setIsActive] = React.useState(branch?.is_active ?? true);
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: branch?.name ?? "",
      code: branch?.code ?? "",
      address: branch?.address ?? "",
      phone: branch?.phone ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const shared = {
      name: values.name.trim(),
      address: values.address.trim() || null,
      phone: values.phone.trim() || null,
      is_active: isActive,
    };

    try {
      if (branch) {
        await branchesApi.update(branch.id, shared);
        toast.success(`Updated ${shared.name}`);
      } else {
        await branchesApi.create({ ...shared, code: values.code.trim() });
        toast.success(`Created ${shared.name}`, {
          description: "Add registers to start taking sales at this location.",
        });
      }
      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError) {
        for (const [field, message] of Object.entries(cause.fieldErrors)) {
          if (field === "name" || field === "code" || field === "address" || field === "phone") {
            setError(field, { message });
          }
        }
      }
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !isSubmitting && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{branch ? `Edit ${branch.name}` : "New branch"}</DialogTitle>
          <DialogDescription>
            A branch is a physical location. Registers, staff and stock all belong to one.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the branch</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name" htmlFor="branch-name" error={errors.name?.message}>
              <Input
                id="branch-name"
                placeholder="Main Street"
                autoComplete="off"
                {...register("name")}
              />
            </Field>

            <Field
              label="Code"
              htmlFor="branch-code"
              error={errors.code?.message}
              hint={isEdit ? "The code cannot be changed after creation." : "Short, unique identifier."}
            >
              <Input
                id="branch-code"
                placeholder="MAIN"
                autoComplete="off"
                disabled={isEdit}
                className="font-mono uppercase"
                {...register("code")}
              />
            </Field>

            <Field
              label="Address"
              htmlFor="branch-address"
              error={errors.address?.message}
              className="sm:col-span-2"
            >
              <Textarea
                id="branch-address"
                rows={2}
                placeholder="Street, city, postcode"
                {...register("address")}
              />
            </Field>

            <Field label="Phone" htmlFor="branch-phone" error={errors.phone?.message}>
              <Input
                id="branch-phone"
                placeholder="Optional"
                autoComplete="off"
                {...register("phone")}
              />
            </Field>
          </div>

          <label className={cn("flex w-fit cursor-pointer items-center gap-2.5", isSubmitting && "opacity-60")}>
            <Checkbox
              checked={isActive}
              disabled={isSubmitting}
              onCheckedChange={(state) => setIsActive(state === true)}
            />
            <span className="text-sm">This branch is active</span>
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {branch ? "Save changes" : "Create branch"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
