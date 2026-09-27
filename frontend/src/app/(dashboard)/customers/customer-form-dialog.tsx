"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
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
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, describeError } from "@/lib/api/client";
import { customersApi, type Customer } from "@/lib/api/customers";
import { cn } from "@/lib/utils";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

const schema = z.object({
  name: z.string().min(1, "Name is required.").max(160, "Use at most 160 characters."),
  phone: z.string().max(32, "Use at most 32 characters."),
  email: z.union([z.literal(""), z.string().email("Enter a valid email address.")]),
  address: z.string().max(255, "Use at most 255 characters."),
  opening_balance: z
    .string()
    .refine((value) => value === "" || MONEY_PATTERN.test(value), "Enter an amount like 100 or 100.50."),
});

type FormValues = z.infer<typeof schema>;

type CustomerFormDialogProps = {
  /** `null` creates a new customer. */
  customer: Customer | null;
  onClose: () => void;
  onSaved: () => void;
};

/** Mounted fresh for each open (the caller supplies a `key`). */
export function CustomerFormDialog({ customer, onClose, onSaved }: CustomerFormDialogProps) {
  const isEdit = customer !== null;
  const [isActive, setIsActive] = React.useState(customer?.is_active ?? true);
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: customer?.name ?? "",
      phone: customer?.phone ?? "",
      email: customer?.email ?? "",
      address: customer?.address ?? "",
      opening_balance: customer?.opening_balance ?? "0",
    },
  });

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const shared = {
      name: values.name.trim(),
      phone: values.phone.trim() || null,
      email: values.email.trim() || null,
      address: values.address.trim() || null,
      is_active: isActive,
    };

    try {
      if (customer) {
        await customersApi.update(customer.id, shared);
        toast.success(`Updated ${shared.name}`);
      } else {
        await customersApi.create({
          ...shared,
          opening_balance: values.opening_balance.trim() || "0",
        });
        toast.success(`Created ${shared.name}`);
      }
      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError) {
        for (const [field, message] of Object.entries(cause.fieldErrors)) {
          if (field === "name" || field === "phone" || field === "email" || field === "address") {
            setError(field, { message });
          }
        }
      }
    }
  }

  return (
    <Dialog open onOpenChange={(next) => !next && !isSubmitting && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{customer ? `Edit ${customer.name}` : "New customer"}</DialogTitle>
          <DialogDescription>
            Customers can buy on account. Their balance is what they currently owe.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the customer</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name" htmlFor="customer-name" error={errors.name?.message}>
              <Input id="customer-name" placeholder="Jane Doe" autoComplete="off" {...register("name")} />
            </Field>

            <Field label="Phone" htmlFor="customer-phone" error={errors.phone?.message}>
              <Input id="customer-phone" placeholder="Optional" autoComplete="off" {...register("phone")} />
            </Field>

            <Field label="Email" htmlFor="customer-email" error={errors.email?.message}>
              <Input
                id="customer-email"
                type="email"
                placeholder="Optional"
                autoComplete="off"
                {...register("email")}
              />
            </Field>

            {isEdit ? null : (
              <Field
                label="Opening balance"
                htmlFor="customer-opening"
                error={errors.opening_balance?.message}
                hint="What they already owed before using this system."
              >
                <Input
                  id="customer-opening"
                  inputMode="decimal"
                  placeholder="0.00"
                  {...register("opening_balance")}
                />
              </Field>
            )}

            <Field
              label="Address"
              htmlFor="customer-address"
              error={errors.address?.message}
              className="sm:col-span-2"
            >
              <Textarea id="customer-address" rows={2} placeholder="Optional" {...register("address")} />
            </Field>
          </div>

          <label
            className={cn(
              "flex w-fit cursor-pointer items-center gap-2.5",
              isSubmitting && "cursor-not-allowed opacity-60",
            )}
          >
            <Checkbox
              checked={isActive}
              disabled={isSubmitting}
              onCheckedChange={(state) => setIsActive(state === true)}
            />
            <span className="text-sm">This customer is active</span>
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {customer ? "Save changes" : "Create customer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
