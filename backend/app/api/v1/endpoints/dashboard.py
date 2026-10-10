"""Dashboard endpoint.

The whole dashboard is one request: the server aggregates, the client displays.
Reads need ``dashboard:view``.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.schemas.dashboard import DashboardSnapshot
from app.services.dashboard import DashboardService
from app.utils.daterange import RangePreset, WindowRequest

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DEFAULT_DASHBOARD_PRESET = "this_week"
_PRESETS = "today | yesterday | this_week | this_month | this_year | custom"


def dashboard_window(
    preset: Annotated[
        RangePreset | None, Query(description=f"Date range preset: {_PRESETS}")
    ] = None,
    date_from: Annotated[date | None, Query(description="Custom range start (ISO date)")] = None,
    date_to: Annotated[date | None, Query(description="Custom range end (ISO date)")] = None,
) -> WindowRequest:
    """Parse the shared date-range parameters, defaulting to the current week."""
    return WindowRequest(
        preset=preset or DEFAULT_DASHBOARD_PRESET, date_from=date_from, date_to=date_to
    )


DashboardWindowDep = Annotated[WindowRequest, Depends(dashboard_window)]
BranchFilter = Annotated[uuid.UUID | None, Query(description="Restrict to one branch")]


@router.get(
    "",
    response_model=DashboardSnapshot,
    dependencies=[Depends(require_permissions(PermissionCode.DASHBOARD_VIEW))],
)
async def dashboard_snapshot(
    session: SessionDep, window: DashboardWindowDep, branch_id: BranchFilter = None
) -> DashboardSnapshot:
    return await DashboardService(session).snapshot(window, branch_id=branch_id)
