"""Cash register sessions: open a till, move cash in and out, close and reconcile."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.register_session import RegisterSessionRepository
from app.schemas.common import Page
from app.schemas.register_session import (
    CashAdjustment,
    RegisterSessionClose,
    RegisterSessionDetail,
    RegisterSessionOpen,
    RegisterSessionRead,
)
from app.services.register_session import RegisterSessionService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/register-sessions", tags=["register-sessions"])


@router.get(
    "",
    response_model=Page[RegisterSessionRead],
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_READ))],
)
async def list_register_sessions(
    session: SessionDep,
    params: Pagination,
    register_id: Annotated[uuid.UUID | None, Query()] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    session_status: Annotated[str | None, Query(alias="status")] = None,
    cashier_id: Annotated[uuid.UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query(description="Opened on or after")] = None,
    date_to: Annotated[date | None, Query(description="Opened on or before")] = None,
    sort: Annotated[str | None, Query(description="e.g. -opened_at")] = None,
) -> Page[RegisterSessionRead]:
    service = RegisterSessionService(session)
    records, total = await service.list_sessions(
        params,
        sort=parse_sort(sort, RegisterSessionRepository.SORTABLE, default="-opened_at"),
        register_id=register_id,
        branch_id=branch_id,
        status=session_status,
        cashier_id=cashier_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Page.build(
        [service.read(record) for record in records],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/open",
    response_model=list[RegisterSessionRead],
    summary="Every open session (for the till picker)",
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_READ))],
)
async def list_open_sessions(
    session: SessionDep,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[RegisterSessionRead]:
    service = RegisterSessionService(session)
    records = await service.list_open(branch_id=branch_id)
    return [service.read(record) for record in records]


@router.get(
    "/current",
    response_model=RegisterSessionDetail | None,
    summary="The open session for a register, or null",
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_READ))],
)
async def current_register_session(
    session: SessionDep,
    register_id: Annotated[uuid.UUID, Query()],
) -> RegisterSessionDetail | None:
    service = RegisterSessionService(session)
    record = await service.current(register_id)
    if record is None:
        return None
    return RegisterSessionDetail(session=service.read(record), summary=service.summary(record))


@router.post(
    "",
    response_model=RegisterSessionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Open a register (opening cash)",
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_OPERATE))],
)
async def open_register_session(
    session: SessionDep, actor: CurrentUser, payload: RegisterSessionOpen
) -> RegisterSessionDetail:
    service = RegisterSessionService(session)
    record = await service.open(payload, actor_id=actor.id)
    return await service.detail(record.id)


@router.get(
    "/{session_id}",
    response_model=RegisterSessionDetail,
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_READ))],
)
async def get_register_session(session: SessionDep, session_id: uuid.UUID) -> RegisterSessionDetail:
    return await RegisterSessionService(session).detail(session_id)


@router.post(
    "/{session_id}/close",
    response_model=RegisterSessionDetail,
    summary="Close a register and reconcile the drawer",
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_OPERATE))],
)
async def close_register_session(
    session: SessionDep,
    actor: CurrentUser,
    session_id: uuid.UUID,
    payload: RegisterSessionClose,
) -> RegisterSessionDetail:
    service = RegisterSessionService(session)
    record = await service.close(session_id, payload, actor_id=actor.id)
    return RegisterSessionDetail(session=service.read(record), summary=service.summary(record))


@router.post(
    "/{session_id}/cash-in",
    response_model=RegisterSessionDetail,
    summary="Put cash into the drawer",
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_OPERATE))],
)
async def cash_in(
    session: SessionDep,
    actor: CurrentUser,
    session_id: uuid.UUID,
    payload: CashAdjustment,
) -> RegisterSessionDetail:
    service = RegisterSessionService(session)
    record = await service.adjust(
        session_id, payload, movement_type="cash_in", actor_id=actor.id
    )
    return RegisterSessionDetail(session=service.read(record), summary=service.summary(record))


@router.post(
    "/{session_id}/cash-out",
    response_model=RegisterSessionDetail,
    summary="Take cash out of the drawer",
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_OPERATE))],
)
async def cash_out(
    session: SessionDep,
    actor: CurrentUser,
    session_id: uuid.UUID,
    payload: CashAdjustment,
) -> RegisterSessionDetail:
    service = RegisterSessionService(session)
    record = await service.adjust(
        session_id, payload, movement_type="cash_out", actor_id=actor.id
    )
    return RegisterSessionDetail(session=service.read(record), summary=service.summary(record))
