import type { ReactNode } from "react";

import { DataTable, type DataTableColumn } from "@/components/data-table/data-table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** A titled card wrapping one report table. */
export function TableCard<T>({
  title,
  description,
  columns,
  rows,
  rowKey,
  emptyTitle,
  className,
}: {
  title: string;
  description?: ReactNode;
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyTitle: string;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <div>
          <CardTitle>{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
      </CardHeader>
      <CardContent>
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={rowKey}
          emptyTitle={emptyTitle}
          emptyDescription="Nothing recorded for this period."
        />
      </CardContent>
    </Card>
  );
}
