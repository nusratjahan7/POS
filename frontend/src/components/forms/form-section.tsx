import * as React from "react";

import { cn } from "@/lib/utils";

type FormSectionProps = {
  title: string;
  description?: string;
  className?: string;
  children: React.ReactNode;
};

/** Grouped fieldset used to break a long form into labelled sections. */
function FormSection({ title, description, className, children }: FormSectionProps) {
  return (
    <section className={cn("flex flex-col gap-4 rounded-lg border p-4", className)}>
      <div className="flex flex-col gap-0.5">
        <h3 className="text-sm font-semibold">{title}</h3>
        {description ? (
          <p className="text-muted-foreground text-xs text-pretty">{description}</p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

export { FormSection };
