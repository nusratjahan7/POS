import type { Metadata } from "next";
import { Suspense } from "react";

import { SessionGate } from "@/components/auth/guards";

import { ForgotPasswordForm } from "./forgot-password-form";

export const metadata: Metadata = {
  title: "Reset your password",
};

export default function ForgotPasswordPage() {
  return (
    <Suspense fallback={<SessionGate message="Loading" />}>
      <ForgotPasswordForm />
    </Suspense>
  );
}
