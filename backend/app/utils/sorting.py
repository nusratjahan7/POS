"""Sort-parameter parsing with an allow-list.

Sorting is never interpolated into SQL: the client sends a field *name*, which
is mapped to a column object from a caller-supplied allow-list. Anything else is
rejected, which removes the whole class of ORDER BY injection.
"""

from __future__ import annotations

from typing import Any

from app.core.exceptions import BadRequestError


def parse_sort(
    raw: str | None,
    allowed: dict[str, Any],
    *,
    default: str | None = None,
) -> tuple[Any, bool] | None:
    """Return ``(column, descending)`` or ``None`` when nothing was requested.

    ``raw`` uses the ``field`` / ``-field`` convention (``-`` = descending).
    ``default`` is applied when ``raw`` is empty; it must be an allowed field.
    """
    field = (raw or "").strip() or (default or "").strip()
    if not field:
        return None

    descending = field.startswith("-")
    name = field[1:] if field[0] in "+-" else field
    if name not in allowed:
        raise BadRequestError(
            f"Cannot sort by '{name}'.",
            code="invalid_sort_field",
            details=[{"field": "sort", "message": f"Allowed: {', '.join(sorted(allowed))}"}],
        )
    return allowed[name], descending
