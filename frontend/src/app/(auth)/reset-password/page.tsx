import type { Metadata } from "next";
import { Suspense } from "react";

import { SessionGate } from "@/components/auth/guards";

import { ResetPasswordForm } from "./reset-password-form";

export const metadata: Metadata = {
  title: "Choose a new password",
};

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<SessionGate message="Loading" />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
