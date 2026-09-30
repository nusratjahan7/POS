"""Resolving a report's date range from a named preset or an explicit range.

The frontend may send a preset ("this_month") or a custom pair of dates. Both
resolve here to one inclusive ``[start, end]`` window of calendar days, so every
report filters the same way. "Today" is supplied by the caller (from the
business's time zone), never assumed to be UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from app.core.exceptions import UnprocessableError

RangePreset = Literal["today", "yesterday", "this_week", "this_month", "this_year", "custom"]

PRESETS: tuple[str, ...] = ("today", "yesterday", "this_week", "this_month", "this_year", "custom")

DEFAULT_PRESET = "this_month"


@dataclass(frozen=True, slots=True)
class WindowRequest:
    """What the query string carried, before resolution."""

    preset: str = DEFAULT_PRESET
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True, slots=True)
class ReportWindow:
    """A resolved, inclusive range of calendar days."""

    start: date
    end: date
    preset: str


def _invalid(message: str, field: str) -> UnprocessableError:
    return UnprocessableError(
        message,
        code="invalid_date_range",
        details=[{"field": field, "message": message}],
    )


def resolve_window(request: WindowRequest, *, today: date) -> ReportWindow:
    """Turn a preset or explicit dates into an inclusive window.

    Explicit dates take precedence: supplying either end is treated as a custom
    range and both are required. Otherwise the preset is resolved relative to
    ``today``. Weeks start on Monday, matching the date picker's `firstDayOfWeek`.
    """
    if request.date_from is not None or request.date_to is not None or request.preset == "custom":
        if request.date_from is None or request.date_to is None:
            raise _invalid(
                "A custom range needs both a start and an end date.", "date_from"
            )
        if request.date_to < request.date_from:
            raise _invalid(
                "The end date cannot be before the start date.", "date_to"
            )
        return ReportWindow(start=request.date_from, end=request.date_to, preset="custom")

    preset = request.preset or DEFAULT_PRESET
    if preset == "today":
        start = end = today
    elif preset == "yesterday":
        start = end = today - timedelta(days=1)
    elif preset == "this_week":
        start, end = today - timedelta(days=today.weekday()), today
    elif preset == "this_month":
        start, end = today.replace(day=1), today
    elif preset == "this_year":
        start, end = today.replace(month=1, day=1), today
    else:
        raise _invalid(f"Unknown date preset '{preset}'.", "preset")

    return ReportWindow(start=start, end=end, preset=preset)
