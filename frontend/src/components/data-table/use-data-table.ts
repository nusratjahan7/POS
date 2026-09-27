"use client";

import * as React from "react";

const DEFAULT_DEBOUNCE_MS = 300;

export type UseDataTableOptions = {
  /** Debounce applied to the search box before it becomes the active query. */
  delay?: number;
};

/**
 * Shared list-screen state: a debounced search box, the query it resolves to,
 * and the current page (reset whenever the query changes). Filters are owned by
 * the caller; call {@link UseDataTableResult.resetPage} when they change.
 */
export function useDataTable({ delay = DEFAULT_DEBOUNCE_MS }: UseDataTableOptions = {}) {
  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [page, setPage] = React.useState(1);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, delay);
    return () => clearTimeout(timer);
  }, [search, delay]);

  const resetPage = React.useCallback(() => setPage(1), []);

  return { search, setSearch, query, page, setPage, resetPage };
}

export type UseDataTableResult = ReturnType<typeof useDataTable>;
