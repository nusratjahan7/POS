import * as React from "react";
import { Database, LockKeyhole, SendHorizonal } from "lucide-react";

import { Brand } from "@/components/layout/brand";

const platformFacts = [
  {
    icon: LockKeyhole,
    title: "JWT sessions",
    description:
      "Short-lived access tokens with rotating refresh tokens held in httpOnly cookies.",
  },
  {
    icon: Database,
    title: "PostgreSQL backed",
    description: "Every branch, user and transaction is stored transactionally.",
  },
  {
    icon: SendHorizonal,
    title: "Versioned REST API",
    description: "All requests go through /api/v1 and share one error envelope.",
  },
];

/**
 * Shared frame for the unauthenticated screens: a focused form column, and a
 * quiet platform panel on wide viewports that gives the login page its own
 * identity instead of a floating card on an empty page.
 */
function AuthShell({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="flex flex-col gap-8 px-6 py-8 sm:px-10 lg:px-14 lg:py-10">
        <Brand />

        <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-7">
          <header className="flex flex-col gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            <p className="text-muted-foreground text-sm text-pretty">{description}</p>
          </header>

          {children}
        </main>

        {footer ? (
          <div className="text-muted-foreground mx-auto w-full max-w-sm text-xs leading-relaxed">
            {footer}
          </div>
        ) : null}
      </div>

      <aside className="bg-sidebar border-sidebar-border hidden flex-col justify-between border-l p-12 lg:flex">
        <div className="flex flex-col gap-3">
          <h2 className="text-xl font-semibold tracking-tight text-balance">
            The counter, the stock and the numbers in one place.
          </h2>
          <p className="text-muted-foreground text-sm text-pretty">
            Sign in to manage sales, inventory and reporting for your branch.
          </p>
        </div>

        <ul className="flex flex-col gap-6">
          {platformFacts.map((fact) => (
            <li key={fact.title} className="flex gap-3">
              <span className="bg-background text-muted-foreground flex size-8 shrink-0 items-center justify-center rounded-md border">
                <fact.icon className="size-4" aria-hidden />
              </span>
              <div className="flex flex-col gap-0.5">
                <p className="text-sm font-medium">{fact.title}</p>
                <p className="text-muted-foreground text-xs leading-relaxed text-pretty">
                  {fact.description}
                </p>
              </div>
            </li>
          ))}
        </ul>

        <p className="text-muted-foreground text-xs">POS · Point of Sale platform</p>
      </aside>
    </div>
  );
}

export { AuthShell };
