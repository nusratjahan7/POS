"use client";

import * as React from "react";
import Link from "next/link";
import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthShell } from "@/components/auth/auth-shell";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { resetPasswordSchema, type ResetPasswordValues } from "@/lib/auth/validation";

/** Codes that mean the link itself is dead and a new one is required. */
const DEAD_LINK_CODES = new Set(["reset_token_expired", "reset_token_used", "invalid_reset_token"]);

export function ResetPasswordForm() {
  const router = useRouter();
  const token = useSearchParams().get("token");
  const [failure, setFailure] = React.useState<{ message: string; dead: boolean } | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  async function onSubmit(values: ResetPasswordValues) {
    if (!token) return;
    setFailure(null);

    try {
      await authApi.resetPassword(token, values.password);
      toast.success("Password updated", {
        description: "Sign in with your new password.",
      });
      router.replace("/login");
    } catch (error) {
      if (error instanceof ApiError) {
        setFailure({ message: error.message, dead: DEAD_LINK_CODES.has(error.code) });
        for (const [field, message] of Object.entries(error.fieldErrors)) {
          if (field === "new_password") setError("password", { message });
        }
        if (error.code === "password_unchanged") {
          setError("password", { message: error.message });
        }
      } else {
        setFailure({
          message: "Could not reach the server. Check your connection and try again.",
          dead: false,
        });
      }
    }
  }

  if (!token) {
    return (
      <AuthShell
        title="Choose a new password"
        description="This reset link is incomplete."
      >
        <ErrorState
          className="px-0 py-0"
          size="compact"
          title="Missing reset token"
          description="Open the link from your email again, or request a fresh one."
          action={
            <Button asChild>
              <Link href="/forgot-password">Request a new link</Link>
            </Button>
          }
        />
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Choose a new password"
      description="Pick something you have not used before. Signing in again will be required afterwards."
      footer={
        <Link
          href="/login"
          className="hover:text-foreground underline-offset-4 hover:underline"
        >
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
        {failure ? (
          <Alert variant="destructive" icon={KeyRound}>
            <AlertTitle>
              {failure.dead ? "This link can no longer be used" : "Could not update your password"}
            </AlertTitle>
            <AlertDescription>
              {failure.message}
              {failure.dead ? (
                <>
                  {" "}
                  <Link
                    href="/forgot-password"
                    className="text-primary font-medium underline-offset-4 hover:underline"
                  >
                    Request a new link
                  </Link>
                  .
                </>
              ) : null}
            </AlertDescription>
          </Alert>
        ) : null}

        <Field
          label="New password"
          htmlFor="password"
          error={errors.password?.message}
          hint="At least 8 characters, with a letter, a digit and a symbol."
        >
          <PasswordInput
            id="password"
            autoComplete="new-password"
            autoFocus
            placeholder="••••••••"
            {...register("password")}
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

        <Button type="submit" disabled={isSubmitting} className="mt-1 w-full">
          {isSubmitting ? <Spinner /> : null}
          {isSubmitting ? "Updating password" : "Update password"}
        </Button>
      </form>
    </AuthShell>
  );
}
