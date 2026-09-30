"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { describeError } from "@/lib/api/client";
import { expenseCategoriesApi } from "@/lib/api/expenses";

/** Manage the buckets expenses are filed under. */
export function ExpenseCategoryDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = React.useState("");

  const listQuery = useQuery({
    queryKey: ["expense-categories", "all"],
    queryFn: () => expenseCategoriesApi.list({ page_size: 100 }),
  });
  const categories = listQuery.data?.items ?? [];

  const createMutation = useMutation({
    mutationFn: () => expenseCategoriesApi.create({ name: name.trim() }),
    onSuccess: () => {
      setName("");
      toast.success("Category added");
      void queryClient.invalidateQueries({ queryKey: ["expense-categories"] });
    },
    onError: (cause) => toast.error(describeError(cause)),
  });

  const removeMutation = useMutation({
    mutationFn: (categoryId: string) => expenseCategoriesApi.remove(categoryId),
    onSuccess: () => {
      toast.success("Category removed");
      void queryClient.invalidateQueries({ queryKey: ["expense-categories"] });
    },
    onError: (cause) => toast.error(describeError(cause)),
  });

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Expense categories</DialogTitle>
          <DialogDescription>Group spending so it can be reported on.</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <form
            className="flex items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (name.trim()) createMutation.mutate();
            }}
          >
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="New category name"
              aria-label="New category name"
              autoComplete="off"
            />
            <Button type="submit" disabled={!name.trim() || createMutation.isPending}>
              {createMutation.isPending ? <Spinner /> : <Plus className="size-4" />}
              Add
            </Button>
          </form>

          <div className="flex max-h-72 flex-col divide-y overflow-y-auto rounded-md border">
            {categories.length === 0 ? (
              <p className="text-muted-foreground p-3 text-sm">No categories yet.</p>
            ) : (
              categories.map((category) => (
                <div
                  key={category.id}
                  className="flex items-center justify-between gap-2 px-3 py-2"
                >
                  <span className="text-sm">{category.name}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Remove ${category.name}`}
                    onClick={() => removeMutation.mutate(category.id)}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
