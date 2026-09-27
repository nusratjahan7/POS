import type { Metadata } from "next";
import { Suspense } from "react";

import { SessionGate } from "@/components/auth/guards";

import { LoginForm } from "./login-form";

export const metadata: Metadata = {
  title: "Sign in",
};

export default function LoginPage() {
  return (
    <Suspense fallback={<SessionGate message="Loading" />}>
      <LoginForm />
    </Suspense>
  );
}
