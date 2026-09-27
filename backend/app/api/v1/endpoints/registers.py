"""Register endpoints.

A register is a till inside a branch — the anchor a future sale resolves through
``business -> branch -> register -> cashier``. No cash movement happens here yet.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.register import RegisterRepository
from app.schemas.common import Page
from app.schemas.register import (
    RegisterCreate,
    RegisterRead,
    RegisterSummary,
    RegisterUpdate,
)
from app.services.register import RegisterService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/registers", tags=["registers"])


@router.get(
    "",
    response_model=Page[RegisterRead],
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_READ))],
)
async def list_registers(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120)] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. name, -created_at")] = None,
) -> Page[RegisterRead]:
    registers, total = await RegisterService(session).list_registers(
        params,
        sort=parse_sort(sort, RegisterRepository.SORTABLE, default="name"),
        search=search,
        branch_id=branch_id,
        is_active=is_active,
    )
    return Page.build(
        [RegisterRead.model_validate(register) for register in registers],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/options",
    response_model=list[RegisterSummary],
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_READ))],
)
async def register_options(
    session: SessionDep,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[RegisterSummary]:
    registers = await RegisterService(session).list_all(branch_id=branch_id)
    return [RegisterSummary.model_validate(register) for register in registers]


@router.post(
    "",
    response_model=RegisterRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_WRITE))],
)
async def create_register(session: SessionDep, payload: RegisterCreate) -> RegisterRead:
    return RegisterRead.model_validate(await RegisterService(session).create(payload))


@router.get(
    "/{register_id}",
    response_model=RegisterRead,
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_READ))],
)
async def get_register(session: SessionDep, register_id: uuid.UUID) -> RegisterRead:
    return RegisterRead.model_validate(await RegisterService(session).get_or_404(register_id))


@router.patch(
    "/{register_id}",
    response_model=RegisterRead,
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_WRITE))],
)
async def update_register(
    session: SessionDep, register_id: uuid.UUID, payload: RegisterUpdate
) -> RegisterRead:
    return RegisterRead.model_validate(await RegisterService(session).update(register_id, payload))


@router.delete(
    "/{register_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.REGISTERS_WRITE))],
)
async def delete_register(session: SessionDep, register_id: uuid.UUID) -> None:
    await RegisterService(session).delete(register_id)
