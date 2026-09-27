"""Branch endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.branch import BranchRepository
from app.schemas.branch import BranchCreate, BranchRead, BranchSummary, BranchUpdate
from app.schemas.common import Page
from app.services.branch import BranchService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get(
    "",
    response_model=Page[BranchRead],
    dependencies=[Depends(require_permissions(PermissionCode.BRANCHES_READ))],
)
async def list_branches(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120)] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. name, -created_at")] = None,
) -> Page[BranchRead]:
    branches, total = await BranchService(session).list_branches(
        params,
        search=search,
        is_active=is_active,
        sort=parse_sort(sort, BranchRepository.SORTABLE, default="name"),
    )
    return Page.build(
        [BranchRead.model_validate(branch) for branch in branches],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/options",
    response_model=list[BranchSummary],
    dependencies=[Depends(require_permissions(PermissionCode.BRANCHES_READ))],
)
async def branch_options(session: SessionDep) -> list[BranchSummary]:
    branches = await BranchService(session).list_all()
    return [BranchSummary.model_validate(branch) for branch in branches]


@router.post(
    "",
    response_model=BranchRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.BRANCHES_WRITE))],
)
async def create_branch(session: SessionDep, payload: BranchCreate) -> BranchRead:
    branch = await BranchService(session).create(payload)
    return BranchRead.model_validate(branch)


@router.get(
    "/{branch_id}",
    response_model=BranchRead,
    dependencies=[Depends(require_permissions(PermissionCode.BRANCHES_READ))],
)
async def get_branch(session: SessionDep, branch_id: uuid.UUID) -> BranchRead:
    return BranchRead.model_validate(await BranchService(session).get_or_404(branch_id))


@router.patch(
    "/{branch_id}",
    response_model=BranchRead,
    dependencies=[Depends(require_permissions(PermissionCode.BRANCHES_WRITE))],
)
async def update_branch(
    session: SessionDep, branch_id: uuid.UUID, payload: BranchUpdate
) -> BranchRead:
    branch = await BranchService(session).update(branch_id, payload)
    return BranchRead.model_validate(branch)


@router.delete(
    "/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.BRANCHES_WRITE))],
)
async def delete_branch(session: SessionDep, branch_id: uuid.UUID) -> None:
    await BranchService(session).delete(branch_id)
