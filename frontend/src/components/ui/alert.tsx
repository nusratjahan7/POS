import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";

import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative flex w-full gap-2.5 rounded-md border px-3.5 py-3 text-sm [&>svg]:mt-px [&>svg]:size-4 [&>svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-muted/50 text-foreground [&>svg]:text-muted-foreground",
        info: "border-info/25 bg-info/8 text-foreground [&>svg]:text-info",
        success: "border-success/30 bg-success/8 text-foreground [&>svg]:text-success",
        warning: "border-warning/35 bg-warning/10 text-foreground [&>svg]:text-warning",
        destructive: "border-destructive/30 bg-destructive/8 text-foreground [&>svg]:text-destructive",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

const variantIcon = {
  default: Info,
  info: Info,
  success: CheckCircle2,
  warning: TriangleAlert,
  destructive: AlertCircle,
} as const;

function Alert({
  className,
  variant = "default",
  icon,
  children,
  ...props
}: React.ComponentProps<"div"> &
  VariantProps<typeof alertVariants> & {
    /** Override the variant's default glyph. */
    icon?: React.ComponentType<{ className?: string }>;
  }) {
  const Icon = icon ?? variantIcon[variant ?? "default"];

  return (
    <div role="alert" data-slot="alert" className={cn(alertVariants({ variant }), className)} {...props}>
      <Icon />
      <div className="flex min-w-0 flex-col gap-1">{children}</div>
    </div>
  );
}

function AlertTitle({ className, ...props }: React.ComponentProps<"p">) {
  return <p data-slot="alert-title" className={cn("font-medium", className)} {...props} />;
}

function AlertDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <div
      data-slot="alert-description"
      className={cn("text-muted-foreground text-xs leading-relaxed text-pretty", className)}
      {...props}
    />
  );
}

export { Alert, AlertDescription, AlertTitle };
