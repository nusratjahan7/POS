"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { useAuth } from "@/components/auth/auth-provider";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { changePasswordSchema, type ChangePasswordValues } from "@/lib/auth/validation";

export function ChangePasswordForm() {
  const { user, changePassword } = useAuth();
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
  });

  async function onSubmit(values: ChangePasswordValues) {
    setFormError(null);

    try {
      await changePassword(values.currentPassword, values.newPassword);
      // The backend revoked every session, so this one is over too; the route
      // guard sends the user to the sign-in screen.
      toast.success("Password updated", {
        description: "For security, you have been signed out everywhere.",
      });
      reset();
    } catch (error) {
      if (error instanceof ApiError) {
        setFormError(error.message);
        if (error.code === "invalid_current_password") {
          setError("currentPassword", { message: error.message });
        }
        for (const [field, message] of Object.entries(error.fieldErrors)) {
          if (field === "new_password") setError("newPassword", { message });
        }
      } else {
        setFormError("Could not reach the server. Check your connection and try again.");
      }
    }
  }

  return (
    <PageContainer>
      <PageHeader
        title="Change password"
        description="Update the password on your own account. You will be signed out of every device afterwards."
      />

      <Card className="max-w-xl">
        <CardHeader>
          <div>
            <CardTitle>Account password</CardTitle>
            <CardDescription>
              Signed in as {user?.email ?? "your account"}.
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
            {formError ? (
              <Alert variant="destructive">
                <AlertTitle>Could not change your password</AlertTitle>
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : null}

            <Field
              label="Current password"
              htmlFor="currentPassword"
              error={errors.currentPassword?.message}
            >
              <PasswordInput
                id="currentPassword"
                autoComplete="current-password"
                autoFocus
                placeholder="••••••••"
                {...register("currentPassword")}
              />
            </Field>

            <Field
              label="New password"
              htmlFor="newPassword"
              error={errors.newPassword?.message}
              hint="At least 8 characters, with a letter, a digit and a symbol."
            >
              <PasswordInput
                id="newPassword"
                autoComplete="new-password"
                placeholder="••••••••"
                {...register("newPassword")}
              />
            </Field>

            <Field
              label="Confirm new password"
              htmlFor="confirmPassword"
              error={errors.confirmPassword?.message}
            >
              <PasswordInput
                id="confirmPassword"
                autoComplete="new-password"
                placeholder="••••••••"
                {...register("confirmPassword")}
              />
            </Field>

            <Alert variant="warning" icon={ShieldCheck}>
              <AlertDescription>
                Changing your password revokes all active sessions, including this one.
              </AlertDescription>
            </Alert>

            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  reset();
                  setFormError(null);
                }}
                disabled={isSubmitting}
              >
                Reset
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? <Spinner /> : null}
                {isSubmitting ? "Updating" : "Update password"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </PageContainer>
  );
}
