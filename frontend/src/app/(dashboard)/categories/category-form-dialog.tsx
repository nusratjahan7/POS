"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, describeError } from "@/lib/api/client";
import { categoriesApi, type Category } from "@/lib/api/catalog";
import { descendantIds, flattenCategoryTree } from "@/lib/catalog-tree";
import { cn } from "@/lib/utils";

const NO_PARENT = "none";

const schema = z.object({
  name: z.string().min(1, "Name is required.").max(120, "Use at most 120 characters."),
  description: z.string().max(255, "Use at most 255 characters."),
});

type FormValues = z.infer<typeof schema>;

type CategoryFormDialogProps = {
  /** `null` creates a new category. */
  category: Category | null;
  onClose: () => void;
  onSaved: () => void;
};

/**
 * Create/edit dialog. Mounted fresh for each open (the caller supplies a `key`),
 * so initial state derives from props once and needs no synchronising effect.
 */
export function CategoryFormDialog({ category, onClose, onSaved }: CategoryFormDialogProps) {
  const isEdit = category !== null;

  const [parentId, setParentId] = React.useState(category?.parent_id ?? NO_PARENT);
  const [imageUrl, setImageUrl] = React.useState<string | null>(category?.image_url ?? null);
  const [isActive, setIsActive] = React.useState(category?.is_active ?? true);
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: category?.name ?? "",
      description: category?.description ?? "",
    },
  });

  // The tree is cached by the parent query; fetch is deduped and usually instant.
  const treeQuery = useQuery({
    queryKey: ["categories", "tree"],
    queryFn: () => categoriesApi.tree(),
  });

  const parentOptions = React.useMemo(() => {
    const nodes = treeQuery.data ?? [];
    // A category may not be reparented under itself or its own descendants.
    const blocked = isEdit && category ? descendantIds(nodes, category.id) : new Set<string>();
    return flattenCategoryTree(nodes).filter((node) => !blocked.has(node.id));
  }, [treeQuery.data, isEdit, category]);

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const payload = {
      name: values.name.trim(),
      description: values.description.trim() || null,
      image_url: imageUrl,
      parent_id: parentId === NO_PARENT ? null : parentId,
      is_active: isActive,
    };

    try {
      if (category) {
        await categoriesApi.update(category.id, payload);
        toast.success(`Updated ${payload.name}`);
      } else {
        await categoriesApi.create(payload);
        toast.success(`Created ${payload.name}`, {
          description: payload.parent_id ? "Added as a sub-category." : undefined,
        });
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
          <DialogTitle>{category ? `Edit ${category.name}` : "New category"}</DialogTitle>
          <DialogDescription>
            Categories can be nested. A parent groups related categories under one heading.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the category</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name" htmlFor="category-name" error={errors.name?.message}>
              <Input
                id="category-name"
                placeholder="Hot drinks"
                autoComplete="off"
                {...register("name")}
              />
            </Field>

            <Field
              label="Parent category"
              htmlFor="category-parent"
              hint="Leave as top level for a root category."
            >
              <Select value={parentId} onValueChange={setParentId}>
                <SelectTrigger id="category-parent" className="w-full">
                  <SelectValue placeholder="Top level" />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  <SelectItem value={NO_PARENT}>Top level (no parent)</SelectItem>
                  {parentOptions.map((option) => (
                    <SelectItem key={option.id} value={option.id}>
                      {"— ".repeat(option.depth)}
                      {option.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field
              label="Description"
              htmlFor="category-description"
              error={errors.description?.message}
              className="sm:col-span-2"
            >
              <Textarea
                id="category-description"
                rows={2}
                placeholder="Optional note for staff"
                {...register("description")}
              />
            </Field>
          </div>

          <ImageUpload
            value={imageUrl}
            onChange={setImageUrl}
            label="Image"
            hint="Optional. A representative image for this category."
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
            <span className="text-sm">This category is active</span>
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : null}
              {category ? "Save changes" : "Create category"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
