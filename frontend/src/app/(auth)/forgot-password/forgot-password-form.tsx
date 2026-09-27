"use client";

import * as React from "react";
import Link from "next/link";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, MailCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthShell } from "@/components/auth/auth-shell";
import { GuestOnly } from "@/components/auth/guards";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/api/auth";
import { ApiError } from "@/lib/api/client";
import { forgotPasswordSchema, type ForgotPasswordValues } from "@/lib/auth/validation";

export function ForgotPasswordForm() {
  const [sentTo, setSentTo] = React.useState<string | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: ForgotPasswordValues) {
    setFormError(null);

    try {
      await authApi.forgotPassword(values.email);
      // The response is intentionally identical for unknown accounts, so the
      // confirmation cannot be used to probe which emails are registered.
      setSentTo(values.email);
      toast.success("Reset link requested", {
        description: "Check your inbox — the link is valid for 30 minutes.",
      });
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? error.message
          : "Could not reach the server. Check your connection and try again.",
      );
    }
  }

  return (
    <GuestOnly>
      <AuthShell
        title="Reset your password"
        description="Enter the email on your staff account and we will send you a link to choose a new password."
        footer={
          <Link
            href="/login"
            className="hover:text-foreground inline-flex items-center gap-1.5 underline-offset-4 hover:underline"
          >
            <ArrowLeft className="size-3" />
            Back to sign in
          </Link>
        }
      >
        {sentTo ? (
          <div className="flex flex-col gap-5">
            <Alert variant="success" icon={MailCheck}>
              <AlertTitle>Check your email</AlertTitle>
              <AlertDescription>
                If an account exists for <span className="text-foreground font-medium">{sentTo}</span>,
                a reset link is on its way. The link can be used once and expires in 30 minutes.
              </AlertDescription>
            </Alert>

            <div className="flex flex-col gap-2">
              <Button asChild variant="outline" className="w-full">
                <Link href="/login">Back to sign in</Link>
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => {
                  setSentTo(null);
                  reset({ email: "" });
                }}
              >
                Use a different email
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
            {formError ? (
              <Alert variant="destructive">
                <AlertTitle>Request failed</AlertTitle>
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : null}

            <Field
              label="Email"
              htmlFor="email"
              error={errors.email?.message}
              hint="We only send a link if the address belongs to an active account."
            >
              <Input
                id="email"
                type="email"
                autoComplete="username"
                autoFocus
                placeholder="you@example.com"
                {...register("email")}
              />
            </Field>

            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? <Spinner /> : null}
              {isSubmitting ? "Sending link" : "Send reset link"}
            </Button>
          </form>
        )}
      </AuthShell>
    </GuestOnly>
  );
}
