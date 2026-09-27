import * as React from "react";

import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type FieldProps = {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  /** Rendered opposite the label, e.g. a "Forgot password?" link. */
  action?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
};

/**
 * Label + control + message, with the accessibility wiring done once so every
 * form in the app behaves the same. The child receives `aria-invalid` and
 * `aria-describedby` pointing at whichever message is showing.
 */
function Field({ label, htmlFor, error, hint, action, className, children }: FieldProps) {
  const messageId = error ? `${htmlFor}-error` : hint ? `${htmlFor}-hint` : undefined;

  const control = React.isValidElement(children)
    ? React.cloneElement(
        children as React.ReactElement<{
          "aria-describedby"?: string;
          "aria-invalid"?: boolean;
        }>,
        {
          "aria-describedby": messageId,
          "aria-invalid": error ? true : undefined,
        },
      )
    : children;

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <Label htmlFor={htmlFor}>{label}</Label>
        {action}
      </div>

      {control}

      {error ? (
        <p id={`${htmlFor}-error`} role="alert" className="text-destructive text-xs">
          {error}
        </p>
      ) : hint ? (
        <p id={`${htmlFor}-hint`} className="text-muted-foreground text-xs">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export { Field };
