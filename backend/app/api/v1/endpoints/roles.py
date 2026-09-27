"""Role endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.role import RoleRepository
from app.schemas.common import Page
from app.schemas.role import RoleCreate, RoleRead, RoleSummary, RoleUpdate
from app.services.role import RoleService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "",
    response_model=Page[RoleRead],
    dependencies=[Depends(require_permissions(PermissionCode.ROLES_READ))],
)
async def list_roles(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120)] = None,
    sort: Annotated[str | None, Query(description="e.g. name, -created_at")] = None,
) -> Page[RoleRead]:
    roles, total = await RoleService(session).list_roles(
        params, search=search, sort=parse_sort(sort, RoleRepository.SORTABLE, default="name")
    )
    return Page.build(
        [RoleRead.model_validate(role) for role in roles],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/options",
    response_model=list[RoleSummary],
    dependencies=[Depends(require_permissions(PermissionCode.ROLES_READ))],
)
async def role_options(session: SessionDep) -> list[RoleSummary]:
    """Lightweight list for assignment dropdowns."""
    roles = await RoleService(session).list_all()
    return [RoleSummary.model_validate(role) for role in roles]


@router.post(
    "",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.ROLES_WRITE))],
)
async def create_role(session: SessionDep, payload: RoleCreate) -> RoleRead:
    role = await RoleService(session).create(payload)
    return RoleRead.model_validate(role)


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permissions(PermissionCode.ROLES_READ))],
)
async def get_role(session: SessionDep, role_id: uuid.UUID) -> RoleRead:
    return RoleRead.model_validate(await RoleService(session).get_or_404(role_id))


@router.patch(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permissions(PermissionCode.ROLES_WRITE))],
)
async def update_role(session: SessionDep, role_id: uuid.UUID, payload: RoleUpdate) -> RoleRead:
    role = await RoleService(session).update(role_id, payload)
    return RoleRead.model_validate(role)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.ROLES_WRITE))],
)
async def delete_role(session: SessionDep, role_id: uuid.UUID) -> None:
    await RoleService(session).delete(role_id)
