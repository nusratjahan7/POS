"""Convert values into JSON-serialisable primitives (for JSONB columns)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def jsonable(value: Any) -> Any:
    """Return a JSON-safe copy of ``value``, recursively.

    UUIDs, ``Decimal``, datetimes and enums become strings; mappings and
    sequences are converted element-wise. Anything else falls back to ``str``.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (uuid.UUID, Decimal, datetime, date)):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(item) for item in value]
    return str(value)
