"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Pencil, Plus, Search, ShieldAlert, UserX } from "lucide-react";
import { toast } from "sonner";

import { ResetPasswordDialog } from "@/app/(dashboard)/users/reset-password-dialog";
import { UserFormDialog } from "@/app/(dashboard)/users/user-form-dialog";
import { Can, useCan } from "@/components/auth/can";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { branchesApi, rolesApi, usersApi, type ManagedUser } from "@/lib/api/rbac";
import { formatDateTime, initials } from "@/lib/format";

export function UsersClient() {
  const canRead = useCan("users:read");
  const canWrite = useCan("users:write");
  const queryClient = useQueryClient();

  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [page, setPage] = React.useState(1);

  // Debounce so typing does not fire a request per keystroke.
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const usersQuery = useQuery({
    queryKey: ["users", { query, page }],
    queryFn: () => usersApi.list({ search: query, page }),
  });
  const rolesQuery = useQuery({ queryKey: ["roles", "options"], queryFn: () => rolesApi.options() });
  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
  });

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<ManagedUser | null>(null);
  const [resetTarget, setResetTarget] = React.useState<ManagedUser | null>(null);

  const users = usersQuery.data?.items ?? [];
  const totalPages = usersQuery.data?.pages ?? 1;

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["users"] });
  }

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(user: ManagedUser) {
    setEditing(user);
    setFormOpen(true);
  }

  async function handleDeactivate(user: ManagedUser) {
    try {
      await usersApi.deactivate(user.id);
      toast.success(`Deactivated ${user.full_name}`, {
        description: "They can no longer sign in.",
      });
      invalidate();
    } catch (cause) {
      toast.error(describeError(cause));
    }
  }

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader title="Users" description="Staff accounts and the access they hold." />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to staff management"
              description="This screen requires the users:read permission. Ask an administrator to grant you a role that includes it."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Users"
        description="Staff accounts and the roles that decide what they can do. Permissions are enforced by the API, not by this screen."
        actions={
          <Can permission="users:write">
            <Button onClick={openCreate}>
              <Plus className="size-4" />
              New user
            </Button>
          </Can>
        }
      />

      <Card>
        <CardHeader className="flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <div className="shrink-0">
            <CardTitle>Staff accounts</CardTitle>
            <CardDescription>
              {usersQuery.data
                ? `${usersQuery.data.total} account${usersQuery.data.total === 1 ? "" : "s"}`
                : "Loading accounts"}
            </CardDescription>
          </div>
          <div className="relative w-full sm:max-w-xs">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search name or email"
              aria-label="Search users"
              className="pl-8"
            />
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {usersQuery.isPending ? (
            <div className="flex flex-col gap-3 p-4">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : usersQuery.error ? (
            <ErrorState
              title="Could not load users"
              description={describeError(usersQuery.error)}
              action={
                <Button variant="outline" onClick={() => void usersQuery.refetch()}>
                  Try again
                </Button>
              }
            />
          ) : users.length === 0 ? (
            <EmptyState
              icon={UserX}
              title={query ? "No accounts match that search" : "No staff accounts yet"}
              description={
                query
                  ? "Try a different name or email address."
                  : "Create the first account and assign it a role."
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Roles</TableHead>
                  <TableHead>Branch</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last sign-in</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <span className="bg-primary/10 text-primary flex size-7 shrink-0 items-center justify-center rounded-full text-[0.6875rem] font-semibold">
                          {initials(user.full_name)}
                        </span>
                        <div className="flex min-w-0 flex-col">
                          <span className="truncate font-medium">{user.full_name}</span>
                          <span className="text-muted-foreground truncate text-xs">
                            {user.email}
                          </span>
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      {user.roles.length === 0 ? (
                        <Badge variant="warning">No roles</Badge>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {user.roles.map((role) => (
                            <Badge key={role.id} variant="neutral">
                              {role.name}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </TableCell>

                    <TableCell className="text-muted-foreground text-sm">
                      {user.branch?.name ?? "—"}
                    </TableCell>

                    <TableCell>
                      <Badge variant={user.is_active ? "success" : "outline"}>
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>

                    <TableCell className="text-muted-foreground text-sm tabular-nums">
                      {formatDateTime(user.last_login_at)}
                    </TableCell>

                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Can permission="users:write">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => openEdit(user)}
                            aria-label={`Edit ${user.full_name}`}
                          >
                            <Pencil className="size-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => setResetTarget(user)}
                            aria-label={`Reset password for ${user.full_name}`}
                          >
                            <KeyRound className="size-4" />
                          </Button>
                        </Can>

                        <Can permission="users:delete">
                          {user.is_active ? (
                            <ConfirmDialog
                              title={`Deactivate ${user.full_name}?`}
                              description="They will be signed out and can no longer sign in. The account is retained, so it can be reactivated later."
                              confirmLabel="Deactivate"
                              onConfirm={() => handleDeactivate(user)}
                              trigger={
                                <Button
                                  variant="ghost"
                                  size="icon-sm"
                                  aria-label={`Deactivate ${user.full_name}`}
                                >
                                  <UserX className="size-4" />
                                </Button>
                              }
                            />
                          ) : (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              disabled
                              aria-label={`${user.full_name} is already inactive`}
                            >
                              <UserX className="size-4" />
                            </Button>
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

        {totalPages > 1 ? (
          <div className="flex items-center justify-between gap-3 border-t px-4 py-3">
            <p className="text-muted-foreground text-xs">
              Page {usersQuery.data?.page ?? 1} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page <= 1}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page >= totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        ) : null}
      </Card>

      {formOpen ? (
        <UserFormDialog
          key={editing?.id ?? "new"}
          user={editing}
          roles={rolesQuery.data ?? []}
          branches={branchesQuery.data ?? []}
          onClose={() => setFormOpen(false)}
          onSaved={invalidate}
        />
      ) : null}

      {resetTarget ? (
        <ResetPasswordDialog user={resetTarget} onClose={() => setResetTarget(null)} />
      ) : null}

      {!canWrite ? (
        <p className="text-muted-foreground text-xs">
          Your role can view staff accounts but not change them.
        </p>
      ) : null}
    </PageContainer>
  );
}
