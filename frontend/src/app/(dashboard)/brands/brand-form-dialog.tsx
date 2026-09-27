"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ImageUpload } from "@/components/forms/image-upload";
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
import { brandsApi, type Brand } from "@/lib/api/catalog";
import { cn } from "@/lib/utils";

const schema = z.object({
  name: z.string().min(1, "Name is required.").max(120, "Use at most 120 characters."),
  description: z.string().max(255, "Use at most 255 characters."),
});

type FormValues = z.infer<typeof schema>;

type BrandFormDialogProps = {
  /** `null` creates a new brand. */
  brand: Brand | null;
  onClose: () => void;
  onSaved: () => void;
};

/** Mounted fresh for each open (the caller supplies a `key`). */
export function BrandFormDialog({ brand, onClose, onSaved }: BrandFormDialogProps) {
  const [logoUrl, setLogoUrl] = React.useState<string | null>(brand?.logo_url ?? null);
  const [isActive, setIsActive] = React.useState(brand?.is_active ?? true);
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: brand?.name ?? "",
      description: brand?.description ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const payload = {
      name: values.name.trim(),
      description: values.description.trim() || null,
      logo_url: logoUrl,
      is_active: isActive,
    };

    try {
      if (brand) {
        await brandsApi.update(brand.id, payload);
        toast.success(`Updated ${payload.name}`);
      } else {
        await brandsApi.create(payload);
        toast.success(`Created ${payload.name}`);
      }
      onSaved();
      onClose();
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError) {
        for (const [field, message] of Object.entries(cause.fieldErrors)) {
          if (field === "name" || field === "description") {
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
          <DialogTitle>{brand ? `Edit ${brand.name}` : "New brand"}</DialogTitle>
          <DialogDescription>
            The manufacturer or label a product belongs to. Brands help customers find what they
            want.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the brand</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <Field label="Name" htmlFor="brand-name" error={errors.name?.message}>
            <Input id="brand-name" placeholder="Lavazza" autoComplete="off" {...register("name")} />
          </Field>

          <Field label="Description" htmlFor="brand-description" error={errors.description?.message}>
            <Textarea
              id="brand-description"
              rows={2}
              placeholder="Optional note about this brand"
              {...register("description")}
            />
          </Field>

          <ImageUpload
            value={logoUrl}
            onChange={setLogoUrl}
            label="Logo"
            hint="Optional. Shown next to products from this brand."
            disabled={isSubmitting}
          />

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
            <span className="text-sm">This brand is active</span>
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {brand ? "Save changes" : "Create brand"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
