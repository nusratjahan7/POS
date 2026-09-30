"""Reporting endpoints.

Reads need ``reports:view``. One endpoint per report returns the JSON the tabs
render; the export endpoint streams the same data as CSV or Excel. Every figure
is computed server-side — the client only displays it.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.schemas.report import (
    FinancialReport,
    InventoryReport,
    PurchaseReport,
    SalesReport,
)
from app.services.report import ReportService
from app.services.report_export import (
    CSV_MEDIA_TYPE,
    HTML_MEDIA_TYPE,
    XLSX_MEDIA_TYPE,
    sections_to_csv,
    sections_to_html,
    sections_to_xlsx,
)
from app.utils.daterange import DEFAULT_PRESET, RangePreset, WindowRequest

router = APIRouter(prefix="/reports", tags=["reports"])

ReportName = Literal["sales", "purchases", "inventory", "financial"]
ExportFormat = Literal["csv", "xlsx", "html"]

_REPORT_TITLES: dict[str, str] = {
    "sales": "Sales report",
    "purchases": "Purchase report",
    "inventory": "Inventory report",
    "financial": "Financial report",
}

_PRESETS = "today | yesterday | this_week | this_month | this_year | custom"


def report_window(
    preset: Annotated[
        RangePreset | None, Query(description=f"Date range preset: {_PRESETS}")
    ] = None,
    date_from: Annotated[date | None, Query(description="Custom range start (ISO date)")] = None,
    date_to: Annotated[date | None, Query(description="Custom range end (ISO date)")] = None,
) -> WindowRequest:
    """Parse the shared date-range query parameters into a resolution request."""
    return WindowRequest(
        preset=preset or DEFAULT_PRESET, date_from=date_from, date_to=date_to
    )


ReportWindowDep = Annotated[WindowRequest, Depends(report_window)]
BranchFilter = Annotated[uuid.UUID | None, Query(description="Restrict to one branch")]


@router.get(
    "/sales",
    response_model=SalesReport,
    dependencies=[Depends(require_permissions(PermissionCode.REPORTS_VIEW))],
)
async def sales_report(
    session: SessionDep, window: ReportWindowDep, branch_id: BranchFilter = None
) -> SalesReport:
    return await ReportService(session).sales(window, branch_id=branch_id)


@router.get(
    "/purchases",
    response_model=PurchaseReport,
    dependencies=[Depends(require_permissions(PermissionCode.REPORTS_VIEW))],
)
async def purchases_report(
    session: SessionDep, window: ReportWindowDep, branch_id: BranchFilter = None
) -> PurchaseReport:
    return await ReportService(session).purchases(window, branch_id=branch_id)


@router.get(
    "/inventory",
    response_model=InventoryReport,
    dependencies=[Depends(require_permissions(PermissionCode.REPORTS_VIEW))],
)
async def inventory_report(
    session: SessionDep, window: ReportWindowDep, branch_id: BranchFilter = None
) -> InventoryReport:
    return await ReportService(session).inventory(window, branch_id=branch_id)


@router.get(
    "/financial",
    response_model=FinancialReport,
    dependencies=[Depends(require_permissions(PermissionCode.REPORTS_VIEW))],
)
async def financial_report(
    session: SessionDep, window: ReportWindowDep, branch_id: BranchFilter = None
) -> FinancialReport:
    return await ReportService(session).financial(window, branch_id=branch_id)


@router.get(
    "/{report}/export",
    dependencies=[Depends(require_permissions(PermissionCode.REPORTS_VIEW))],
)
async def export_report(
    session: SessionDep,
    report: ReportName,
    window: ReportWindowDep,
    export_format: Annotated[ExportFormat, Query(alias="format")] = "csv",
    branch_id: BranchFilter = None,
) -> Response:
    """Download a report as CSV, a real Excel workbook (.xlsx), or printable HTML."""
    sections, covered = await ReportService(session).export(
        report, window, branch_id=branch_id
    )
    if export_format == "csv":
        content = sections_to_csv(sections)
        media_type = CSV_MEDIA_TYPE
    elif export_format == "xlsx":
        content = sections_to_xlsx(sections)
        media_type = XLSX_MEDIA_TYPE
    else:
        content = sections_to_html(
            sections,
            title=_REPORT_TITLES[report],
            subtitle=f"{covered.start.isoformat()} to {covered.end.isoformat()}",
        )
        media_type = HTML_MEDIA_TYPE

    filename = f"{report}-{covered.start.isoformat()}_{covered.end.isoformat()}.{export_format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
