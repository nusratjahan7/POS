"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { ApiError, describeError } from "@/lib/api/client";
import { paymentMethodsApi, type PaymentKind, type PaymentMethod } from "@/lib/api/settings";
import { cn } from "@/lib/utils";

const KIND_OPTIONS: { value: PaymentKind; label: string }[] = [
  { value: "cash", label: "Cash" },
  { value: "card", label: "Card" },
  { value: "mobile", label: "Mobile wallet" },
  { value: "bank", label: "Bank transfer" },
  { value: "other", label: "Other" },
];

const schema = z.object({
  name: z.string().min(1, "Name is required.").max(80, "Use at most 80 characters."),
  code: z
    .string()
    .min(1, "Code is required.")
    .max(40, "Use at most 40 characters.")
    .regex(/^[A-Za-z0-9._-]+$/, "Use letters, digits, dot, hyphen or underscore only."),
  description: z.string().max(255, "Use at most 255 characters."),
  sort_order: z.coerce
    .number()
    .int("Use a whole number.")
    .min(0, "Cannot be negative.")
    .max(1000, "Cannot exceed 1000."),
});

type FormValues = z.infer<typeof schema>;

type PaymentMethodFormDialogProps = {
  /** `null` creates a new method. */
  method: PaymentMethod | null;
  onClose: () => void;
  onSaved: () => void;
};

/** Mounted fresh for each open (the caller supplies a `key`). */
export function PaymentMethodFormDialog({ method, onClose, onSaved }: PaymentMethodFormDialogProps) {
  const isSystem = method?.is_system ?? false;
  const [kind, setKind] = React.useState<PaymentKind>(method?.kind ?? "other");
  const [isActive, setIsActive] = React.useState(method?.is_active ?? true);
  const [opensDrawer, setOpensDrawer] = React.useState(method?.opens_cash_drawer ?? false);
  const [needsReference, setNeedsReference] = React.useState(
    method?.requires_reference ?? false,
  );
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: method?.name ?? "",
      code: method?.code ?? "",
      description: method?.description ?? "",
      sort_order: method?.sort_order ?? 0,
    },
  });

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const shared = {
      name: values.name.trim(),
      kind,
      description: values.description.trim() || null,
      is_active: isActive,
      opens_cash_drawer: opensDrawer,
      requires_reference: needsReference,
      sort_order: values.sort_order,
    };

    try {
      if (method) {
        await paymentMethodsApi.update(method.id, {
          ...shared,
          // Seeded methods keep their code — the API rejects a change anyway.
          ...(isSystem ? {} : { code: values.code.trim() }),
        });
        toast.success(`Updated ${shared.name}`);
      } else {
        await paymentMethodsApi.create({ ...shared, code: values.code.trim() });
        toast.success(`Created ${shared.name}`);
      }
      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError) {
        for (const [fieldName, message] of Object.entries(cause.fieldErrors)) {
          if (fieldName === "name" || fieldName === "code") {
            setError(fieldName, { message });
          }
        }
      }
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !isSubmitting && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{method ? `Edit ${method.name}` : "New payment method"}</DialogTitle>
          <DialogDescription>
            How a customer can pay. The till will offer active methods in the order below.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the payment method</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name" htmlFor="payment-name" error={errors.name?.message}>
              <Input
                id="payment-name"
                placeholder="bKash"
                autoComplete="off"
                {...register("name")}
              />
            </Field>

            <Field
              label="Code"
              htmlFor="payment-code"
              error={errors.code?.message}
              hint={isSystem ? "Built-in codes cannot be changed." : "Short, unique identifier."}
            >
              <Input
                id="payment-code"
                placeholder="BKASH"
                autoComplete="off"
                disabled={isSystem}
                className="font-mono uppercase"
                {...register("code")}
              />
            </Field>

            <Field label="Type" htmlFor="payment-kind">
              <Select value={kind} onValueChange={(value) => setKind(value as PaymentKind)}>
                <SelectTrigger id="payment-kind" className="w-full">
                  <SelectValue placeholder="Select a type" />
                </SelectTrigger>
                <SelectContent>
                  {KIND_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field
              label="Display order"
              htmlFor="payment-order"
              error={errors.sort_order?.message}
              hint="Lower numbers appear first."
            >
              <Input
                id="payment-order"
                type="number"
                min="0"
                max="1000"
                step="1"
                inputMode="numeric"
                {...register("sort_order")}
              />
            </Field>

            <Field
              label="Description"
              htmlFor="payment-description"
              error={errors.description?.message}
              className="sm:col-span-2"
            >
              <Input
                id="payment-description"
                placeholder="Optional note shown to cashiers"
                autoComplete="off"
                {...register("description")}
              />
            </Field>
          </div>

          <div className="flex flex-col gap-3 rounded-md border p-3">
            <label
              className={cn(
                "flex cursor-pointer items-center gap-2.5",
                isSubmitting && "cursor-not-allowed opacity-60",
              )}
            >
              <Checkbox
                checked={opensDrawer}
                disabled={isSubmitting}
                onCheckedChange={(state) => setOpensDrawer(state === true)}
              />
              <span className="flex flex-col">
                <span className="text-sm font-medium">Opens the cash drawer</span>
                <span className="text-muted-foreground text-xs">Typically cash only.</span>
              </span>
            </label>

            <label
              className={cn(
                "flex cursor-pointer items-center gap-2.5",
                isSubmitting && "cursor-not-allowed opacity-60",
              )}
            >
              <Checkbox
                checked={needsReference}
                disabled={isSubmitting}
                onCheckedChange={(state) => setNeedsReference(state === true)}
              />
              <span className="flex flex-col">
                <span className="text-sm font-medium">Requires a reference</span>
                <span className="text-muted-foreground text-xs">
                  Card, wallet and bank tenders record a transaction reference.
                </span>
              </span>
            </label>
          </div>

          <label className={cn("flex w-fit cursor-pointer items-center gap-2.5", isSubmitting && "opacity-60")}>
            <Checkbox
              checked={isActive}
              disabled={isSubmitting}
              onCheckedChange={(state) => setIsActive(state === true)}
            />
            <span className="text-sm">This method is active</span>
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {method ? "Save changes" : "Create method"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
