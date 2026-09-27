"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { RoleFormDialog } from "@/app/(dashboard)/roles/role-form-dialog";
import { Can, useCan } from "@/components/auth/can";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { describeError } from "@/lib/api/client";
import { permissionsApi, rolesApi, type Role } from "@/lib/api/rbac";
import { humanizeResource } from "@/lib/auth/permissions";

const MAX_RESOURCE_BADGES = 4;

function ResourceBadges({ role }: { role: Role }) {
  const resources = [...new Set(role.permissions.map((permission) => permission.resource))].sort();
  const visible = resources.slice(0, MAX_RESOURCE_BADGES);
  const overflow = resources.length - visible.length;

  if (resources.length === 0) {
    return <span className="text-muted-foreground text-xs">No permissions granted</span>;
  }

  return (
    <div className="flex flex-wrap items-center gap-1">
      {visible.map((resource) => (
        <Badge key={resource} variant="neutral">
          {humanizeResource(resource)}
        </Badge>
      ))}
      {overflow > 0 ? <Badge variant="outline">+{overflow}</Badge> : null}
    </div>
  );
}

export function RolesClient() {
  const canWrite = useCan("roles:write");
  const queryClient = useQueryClient();

  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: () => rolesApi.list() });
  const catalogQuery = useQuery({
    queryKey: ["permissions"],
    queryFn: () => permissionsApi.list(),
    // The catalog is code-defined and never changes while the app is running.
    staleTime: Infinity,
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Role | null>(null);

  const roles = rolesQuery.data?.items ?? [];
  const catalog = catalogQuery.data ?? [];

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["roles"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(role: Role) {
    setEditing(role);
    setFormOpen(true);
  }

  async function handleDelete(role: Role) {
    try {
      await rolesApi.remove(role.id);
      toast.success(`Deleted ${role.name}`);
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  return (
    <PageContainer>
      <PageHeader
        title="Roles & permissions"
        description="Each role is a bundle of granular permissions. Assign roles to staff to grant capabilities — the API enforces every one of them."
        actions={
          <Can permission="roles:write">
            <Button onClick={openCreate} disabled={catalog.length === 0}>
              <Plus className="size-4" />
              New role
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-start gap-3 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <CardTitle>Defined roles</CardTitle>
            <CardDescription>
              System roles are owned by the application and cannot be renamed or deleted.
            </CardDescription>
          </div>
          <Badge variant="outline">{roles.length} roles</Badge>
        </CardHeader>

        <CardContent className="p-0">
          {rolesQuery.isPending ? (
            <div className="flex flex-col gap-3 p-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : rolesQuery.error ? (
            <ErrorState
              title="Could not load roles"
              description={describeError(rolesQuery.error)}
              action={
                <Button variant="outline" onClick={() => void rolesQuery.refetch()}>
                  Try again
                </Button>
              }
            />
          ) : roles.length === 0 ? (
            <EmptyState
              icon={Lock}
              title="No roles defined"
              description="Create a role to start granting permissions to your staff."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role</TableHead>
                  <TableHead>Permissions</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles.map((role) => (
                  <TableRow key={role.id}>
                    <TableCell className="max-w-[22rem]">
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium">{role.name}</span>
                        {role.description ? (
                          <span className="text-muted-foreground text-xs leading-relaxed">
                            {role.description}
                          </span>
                        ) : null}
                      </div>
                    </TableCell>

                    <TableCell>
                      <ResourceBadges role={role} />
                    </TableCell>

                    <TableCell>
                      <Badge variant={role.is_system ? "info" : "outline"}>
                        {role.is_system ? "System" : "Custom"}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                disabled={!canWrite || role.name === "Administrator"}
                                onClick={() => openEdit(role)}
                                aria-label={`Edit ${role.name}`}
                              >
                                <Pencil className="size-4" />
                              </Button>
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            {role.name === "Administrator"
                              ? "The Administrator role cannot be changed"
                              : canWrite
                                ? "Edit role"
                                : "Requires roles:write"}
                          </TooltipContent>
                        </Tooltip>

                        <Can permission="roles:write">
                          {role.is_system ? (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span>
                                  <Button
                                    variant="ghost"
                                    size="icon-sm"
                                    disabled
                                    aria-label={`${role.name} cannot be deleted`}
                                  >
                                    <Trash2 className="size-4" />
                                  </Button>
                                </span>
                              </TooltipTrigger>
                              <TooltipContent>System roles cannot be deleted</TooltipContent>
                            </Tooltip>
                          ) : (
                            <ConfirmDialog
                              title={`Delete ${role.name}?`}
                              description="The role is removed for every user who holds it. This cannot be undone."
                              confirmLabel="Delete role"
                              onConfirm={() => handleDelete(role)}
                              trigger={
                                <Button
                                  variant="ghost"
                                  size="icon-sm"
                                  aria-label={`Delete ${role.name}`}
                                >
                                  <Trash2 className="size-4" />
                                </Button>
                              }
                            />
                          )}
                        </Can>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {formOpen ? (
        <RoleFormDialog
          key={editing?.id ?? "new"}
          role={editing}
          catalog={catalog}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}
    </PageContainer>
  );
}
