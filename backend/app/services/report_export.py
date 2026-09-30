"""Turning report data into downloadable files.

Every writer takes the same intermediate shape — a list of titled sections of
columns and rows — so a report is described once and emitted as CSV, as a real
``.xlsx`` workbook (one sheet per section), or as a standalone printable HTML
document the browser renders to PDF via its print dialog.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HTML_MEDIA_TYPE = "text/html; charset=utf-8"

#: Excel forbids these in a sheet name and caps the length at 31 characters.
_INVALID_SHEET_CHARS = "[]:*?/\\"

_ESCAPE_RE = re.compile(r"[&<>\"']")
_ESCAPES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}

_HTML_STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 32px; color: #111827;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
h1 { margin: 0; font-size: 20px; }
p.subtitle { margin: 4px 0 8px; color: #4b5563; font-size: 13px; }
h2 {
  margin: 24px 0 8px; font-size: 13px; text-transform: uppercase;
  letter-spacing: 0.04em; color: #374151;
}
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { border-bottom: 1px solid #e5e7eb; padding: 6px 8px; text-align: left; }
th { background: #f3f4f6; font-weight: 600; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
@media print { body { padding: 0; } @page { margin: 16mm; } }
"""


@dataclass(frozen=True, slots=True)
class ReportSection:
    title: str
    columns: list[str]
    rows: list[list[Any]] = field(default_factory=list)


def _escape(value: object) -> str:
    return _ESCAPE_RE.sub(lambda match: _ESCAPES[match.group(0)], str(value))


def sections_to_csv(sections: list[ReportSection]) -> bytes:
    """One CSV: a title row, the header row, the data, then a blank separator."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for index, section in enumerate(sections):
        writer.writerow([section.title])
        writer.writerow(section.columns)
        writer.writerows(section.rows)
        if index < len(sections) - 1:
            writer.writerow([])
    # A BOM so Excel opens UTF-8 correctly.
    return buffer.getvalue().encode("utf-8-sig")


def _safe_sheet_title(title: str, used: set[str]) -> str:
    cleaned = "".join(" " if char in _INVALID_SHEET_CHARS else char for char in title).strip()
    cleaned = (cleaned or "Sheet")[:31]
    candidate = cleaned
    suffix = 2
    while candidate.lower() in used:
        tail = f" ({suffix})"
        candidate = f"{cleaned[: 31 - len(tail)]}{tail}"
        suffix += 1
    used.add(candidate.lower())
    return candidate


def sections_to_xlsx(sections: list[ReportSection]) -> bytes:
    """A workbook with one bold-headed sheet per section."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    used: set[str] = set()

    for section in sections:
        sheet = workbook.create_sheet(title=_safe_sheet_title(section.title, used))
        sheet.append(section.columns)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in section.rows:
            sheet.append(row)
        for column_cells in sheet.columns:
            widest = max(
                (len(str(cell.value)) for cell in column_cells if cell.value is not None),
                default=0,
            )
            letter = column_cells[0].column_letter
            sheet.column_dimensions[letter].width = min(max(widest + 2, 10), 48)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def sections_to_html(
    sections: list[ReportSection], *, title: str, subtitle: str = ""
) -> bytes:
    """A standalone, print-ready document — the browser's Save-as-PDF source."""
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8"/>',
        f"<title>{_escape(title)}</title>",
        f"<style>{_HTML_STYLE}</style></head><body>",
        f"<h1>{_escape(title)}</h1>",
    ]
    if subtitle:
        parts.append(f'<p class="subtitle">{_escape(subtitle)}</p>')

    for section in sections:
        numeric = [
            bool(section.rows)
            and all(isinstance(row[index], (int, float, Decimal)) for row in section.rows)
            for index in range(len(section.columns))
        ]
        parts.append(f"<h2>{_escape(section.title)}</h2><table><thead><tr>")
        for index, column in enumerate(section.columns):
            css = ' class="num"' if numeric[index] else ""
            parts.append(f"<th{css}>{_escape(column)}</th>")
        parts.append("</tr></thead><tbody>")
        for row in section.rows:
            parts.append("<tr>")
            for index, value in enumerate(row):
                css = ' class="num"' if index < len(numeric) and numeric[index] else ""
                parts.append(f"<td{css}>{_escape(value)}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

    parts.append("</body></html>")
    return "".join(parts).encode("utf-8")


__all__ = [
    "CSV_MEDIA_TYPE",
    "HTML_MEDIA_TYPE",
    "XLSX_MEDIA_TYPE",
    "ReportSection",
    "sections_to_csv",
    "sections_to_html",
    "sections_to_xlsx",
]
