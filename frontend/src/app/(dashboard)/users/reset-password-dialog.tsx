"use client";

import * as React from "react";
import { toast } from "sonner";

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
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import { describeError } from "@/lib/api/client";
import { usersApi, type ManagedUser } from "@/lib/api/rbac";
import { passwordSchema } from "@/lib/auth/validation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

const schema = z
  .object({
    password: passwordSchema,
    confirm: z.string().min(1, "Confirm the new password."),
  })
  .refine((values) => values.password === values.confirm, {
    path: ["confirm"],
    message: "Passwords do not match.",
  });

type FormValues = z.infer<typeof schema>;

type ResetPasswordDialogProps = {
  user: ManagedUser;
  onClose: () => void;
};

/** Administrative password reset — the account holder is not asked for the old one. */
export function ResetPasswordDialog({ user, onClose }: ResetPasswordDialogProps) {
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm: "" },
  });

  async function onSubmit(values: FormValues) {
    setFormError(null);

    try {
      await usersApi.setPassword(user.id, values.password);
      toast.success(`Password reset for ${user.full_name}`, {
        description: "Share the new password with them securely.",
      });
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !isSubmitting && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reset password</DialogTitle>
          <DialogDescription>
            Set a new password for {user.full_name} ({user.email}).
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not reset the password</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <Field
            label="New password"
            htmlFor="reset-password"
            error={errors.password?.message}
            hint="At least 8 characters, with a letter, a digit and a symbol."
          >
            <PasswordInput
              id="reset-password"
              autoComplete="new-password"
              autoFocus
              placeholder="••••••••"
              {...register("password")}
            />
          </Field>

          <Field
            label="Confirm new password"
            htmlFor="reset-confirm"
            error={errors.confirm?.message}
          >
            <PasswordInput
              id="reset-confirm"
              autoComplete="new-password"
              placeholder="••••••••"
              {...register("confirm")}
            />
          </Field>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              Reset password
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
