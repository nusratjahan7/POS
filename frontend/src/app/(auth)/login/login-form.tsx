"use client";

import * as React from "react";
import Link from "next/link";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthShell } from "@/components/auth/auth-shell";
import { useAuth } from "@/components/auth/auth-provider";
import { GuestOnly } from "@/components/auth/guards";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api/client";
import { loginSchema, type LoginValues } from "@/lib/auth/validation";

export function LoginForm() {
  const { login } = useAuth();
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginValues) {
    setFormError(null);

    try {
      const user = await login(values.email, values.password);
      // `GuestOnly` performs the redirect once the session is established.
      toast.success(`Welcome back, ${user.full_name.split(" ")[0]}.`);
    } catch (error) {
      if (error instanceof ApiError) {
        setFormError(error.message);
        for (const [field, message] of Object.entries(error.fieldErrors)) {
          if (field === "email" || field === "password") setError(field, { message });
        }
      } else {
        setFormError("Could not reach the server. Check your connection and try again.");
      }
      // Never leave a rejected password sitting in the field.
      setValue("password", "");
    }
  }

  return (
    <GuestOnly>
      <AuthShell
        title="Sign in"
        description="Use your staff account to open the register and manage your branch."
        footer="Accounts are created by an administrator. If you are locked out, use the reset link instead of creating a new account."
      >
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not sign you in</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <Field label="Email" htmlFor="email" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              autoFocus
              placeholder="you@example.com"
              {...register("email")}
            />
          </Field>

          <Field
            label="Password"
            htmlFor="password"
            error={errors.password?.message}
            action={
              <Link
                href="/forgot-password"
                className="text-muted-foreground hover:text-foreground text-xs underline-offset-4 hover:underline"
              >
                Forgot password?
              </Link>
            }
          >
            <PasswordInput
              id="password"
              autoComplete="current-password"
              placeholder="••••••••"
              {...register("password")}
            />
          </Field>

          <Button type="submit" disabled={isSubmitting} className="mt-1 w-full">
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Signing in" : "Sign in"}
          </Button>
        </form>
      </AuthShell>
    </GuestOnly>
  );
}
