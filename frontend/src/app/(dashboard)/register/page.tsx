import type { Metadata } from "next";

import { RegisterClient } from "./register-client";

export const metadata: Metadata = {
  title: "Register",
};

export default function RegisterPage() {
  return <RegisterClient />;
}
