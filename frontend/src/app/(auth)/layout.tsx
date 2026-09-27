import type { Metadata } from "next";

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

/** Unauthenticated screens: never indexed, and laid out by `AuthShell`. */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <div className="bg-background min-h-svh">{children}</div>;
}
