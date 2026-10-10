"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { ScrollText, ShieldAlert } from "lucide-react";

import { useCan } from "@/components/auth/can";
import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { auditApi, type AuditLogEntry } from "@/lib/api/audit";
import { formatDateTime } from "@/lib/format";

const MODULES = [
  "all",
  "auth",
  "catalog",
  "inventory",
  "sales",
  "purchases",
  "users",
  "rbac",
  "settings",
] as const;

const PAGE_SIZE = 20;

export function AuditClient() {
  const canRead = useCan("audit:read");

  const [module, setModule] = React.useState<string>("all");
  const [search, setSearch] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [selected, setSelected] = React.useState<AuditLogEntry | null>(null);

  const params = {
    page,
    page_size: PAGE_SIZE,
    module: module === "all" ? undefined : module,
    search: search.trim() || undefined,
  };

  const query = useQuery({
    queryKey: ["audit-logs", params],
    queryFn: () => auditApi.list(params),
    enabled: canRead,
  });

  if (!canRead) {
    return (
      <PageContainer>
        <PageHeader
          title="Audit log"
          description="A record of sensitive actions across the platform."
        />
        <Card>
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to the audit log"
              description="This screen requires the audit:read permission."
            />
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const columns: DataTableColumn<AuditLogEntry>[] = [
    {
      id: "created_at",
      header: "Time",
      cell: (row) => (
        <span className="text-muted-foreground text-xs whitespace-nowrap">
          {formatDateTime(row.created_at)}
        </span>
      ),
    },
    {
      id: "actor",
      header: "Actor",
      cell: (row) => (
        <span className="text-sm">
          {row.user_name ?? "System"}
          {row.user_email ? (
            <span className="text-muted-foreground block text-xs">{row.user_email}</span>
          ) : null}
        </span>
      ),
    },
    {
      id: "action",
      header: "Action",
      cell: (row) => <span className="font-medium">{row.action}</span>,
    },
    {
      id: "module",
      header: "Module",
      hideBelow: "md",
      cell: (row) => <Badge variant="neutral">{row.module}</Badge>,
    },
    {
      id: "entity",
      header: "Entity",
      hideBelow: "lg",
      cell: (row) => (
        <span className="text-muted-foreground text-xs">
          {row.entity ?? "—"}
          {row.entity_id ? ` · ${row.entity_id.slice(0, 8)}` : ""}
        </span>
      ),
    },
    {
      id: "ip_address",
      header: "IP",
      hideBelow: "lg",
      cell: (row) => (
        <span className="text-muted-foreground text-xs tabular-nums">
          {row.ip_address ?? "—"}
        </span>
      ),
    },
    {
      id: "inspect",
      header: "",
      align: "right",
      cell: (row) => (
        <Button variant="ghost" size="sm" onClick={() => setSelected(row)}>
          View
        </Button>
      ),
    },
  ];

  const items = query.data?.items ?? [];
  const pages = query.data?.pages ?? 1;

  return (
    <PageContainer>
      <PageHeader
        title="Audit log"
        description="Sign-ins, price changes, refunds, stock adjustments, and account or permission changes."
      />

      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
          placeholder="Search action, entity or user"
          className="w-64"
          aria-label="Search the audit log"
        />
        <Select
          value={module}
          onValueChange={(value) => {
            setModule(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-44" aria-label="Filter by module">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MODULES.map((name) => (
              <SelectItem key={name} value={name}>
                {name === "all" ? "All modules" : name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent>
          <DataTable
            columns={columns}
            rows={items}
            rowKey={(row) => row.id}
            isLoading={query.isPending}
            error={query.isError ? query.error : undefined}
            onRetry={() => void query.refetch()}
            emptyIcon={ScrollText}
            emptyTitle="No audit entries"
            emptyDescription="Nothing matches these filters yet."
          />
        </CardContent>
      </Card>

      {pages > 1 ? (
        <div className="flex items-center justify-between gap-3">
          <span className="text-muted-foreground text-xs">
            Page {page} of {pages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pages}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}

      <Dialog
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>{selected?.action ?? "Audit entry"}</DialogTitle>
            <DialogDescription>
              {selected
                ? `${selected.module}${selected.entity ? ` · ${selected.entity}` : ""} · ${formatDateTime(selected.created_at)}`
                : ""}
            </DialogDescription>
          </DialogHeader>
          {selected ? <AuditDiff entry={selected} /> : null}
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}

function AuditDiff({ entry }: { entry: AuditLogEntry }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <JsonPanel title="Before" data={entry.old_data} />
        <JsonPanel title="After" data={entry.new_data} />
      </div>
      <p className="text-muted-foreground text-xs">
        {entry.user_email ?? "System"}
        {entry.ip_address ? ` · ${entry.ip_address}` : ""}
      </p>
    </div>
  );
}

function JsonPanel({ title, data }: { title: string; data: Record<string, unknown> | null }) {
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <span className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
        {title}
      </span>
      <pre className="bg-muted/50 max-h-72 overflow-auto rounded-md border p-2 text-xs">
        {data && Object.keys(data).length > 0 ? JSON.stringify(data, null, 2) : "—"}
      </pre>
    </div>
  );
}
