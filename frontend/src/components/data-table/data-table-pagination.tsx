"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type DataTablePaginationProps = {
  page: number;
  pages: number;
  total?: number;
  onPageChange: (page: number) => void;
  className?: string;
};

/** Previous/Next pager. Renders nothing when everything fits on one page. */
function DataTablePagination({
  page,
  pages,
  total,
  onPageChange,
  className,
}: DataTablePaginationProps) {
  if (pages <= 1) return null;

  return (
    <div className={cn("flex items-center justify-between gap-3 pt-4", className)}>
      <p className="text-muted-foreground text-xs">
        Page {page} of {pages}
        {typeof total === "number" ? ` · ${total} total` : ""}
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(Math.min(pages, page + 1))}
          disabled={page >= pages}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

export { DataTablePagination };
