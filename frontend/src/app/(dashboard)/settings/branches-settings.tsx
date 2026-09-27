"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Pencil, Plus, Search, ShieldAlert, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { BranchFormDialog } from "@/app/(dashboard)/settings/branch-form-dialog";
import { SettingsCard } from "@/app/(dashboard)/settings/settings-card";
import { Can, useCan } from "@/components/auth/can";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { describeError } from "@/lib/api/client";
import { branchesApi, type Branch } from "@/lib/api/rbac";

export function BranchesSettings() {
  const canRead = useCan("branches:read");
  const queryClient = useQueryClient();

  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");

  React.useEffect(() => {
    const timer = setTimeout(() => setQuery(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const branchesQuery = useQuery({
    queryKey: ["branches", { query }],
    queryFn: () => branchesApi.list({ search: query }),
    enabled: canRead,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Branch | null>(null);

  const branches = branchesQuery.data?.items ?? [];

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["branches"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(branch: Branch) {
    setEditing(branch);
    setFormOpen(true);
  }

  async function handleDelete(branch: Branch) {
    try {
      await branchesApi.remove(branch.id);
      toast.success(`Deleted ${branch.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  if (!canRead) {
    return (
      <SettingsCard title="Branches" description="The physical locations you operate from.">
        <ErrorState
          icon={ShieldAlert}
          title="You cannot view branches"
          description="This section requires the branches:read permission."
        />
      </SettingsCard>
    );
  }

  return (
    <SettingsCard
      title="Branches"
      description="Each branch is one location. Registers, staff and stock are scoped to a branch."
      action={
        <Can permission="branches:write">
          <Button onClick={openCreate}>
            <Plus className="size-4" />
            New branch
          </Button>
        </Can>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="relative w-full max-w-xs">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search name or code"
            aria-label="Search branches"
            className="pl-8"
          />
        </div>

        {branchesQuery.isPending ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : branchesQuery.error ? (
          <ErrorState
            title="Could not load branches"
            description={describeError(branchesQuery.error)}
            action={
              <Button variant="outline" onClick={() => void branchesQuery.refetch()}>
                Try again
              </Button>
            }
          />
        ) : branches.length === 0 ? (
          <EmptyState
            icon={Building2}
            size="compact"
            title={query ? "No branches match that search" : "No branches yet"}
            description={
              query
                ? "Try a different name or code."
                : "Create the first branch to start configuring registers."
            }
          />
        ) : (
          <div className="overflow-hidden rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Branch</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {branches.map((branch) => (
                  <TableRow key={branch.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium">{branch.name}</span>
                        {branch.address ? (
                          <span className="text-muted-foreground truncate text-xs">
                            {branch.address}
                          </span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{branch.code}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {branch.phone ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={branch.is_active ? "success" : "outline"}>
                        {branch.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Can permission="branches:write">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => openEdit(branch)}
                            aria-label={`Edit ${branch.name}`}
                          >
                            <Pencil className="size-4" />
                          </Button>

                          <ConfirmDialog
                            title={`Delete ${branch.name}?`}
                            description="The branch is removed for this workspace. It must have no staff or registers first."
                            confirmLabel="Delete branch"
                            onConfirm={() => handleDelete(branch)}
                            trigger={
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                aria-label={`Delete ${branch.name}`}
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            }
                          />
                        </Can>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {formOpen ? (
        <BranchFormDialog
          key={editing?.id ?? "new"}
          branch={editing}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}
    </SettingsCard>
  );
}
