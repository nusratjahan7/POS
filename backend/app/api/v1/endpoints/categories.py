from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.category import CategoryRepository
from app.schemas.category import (
    CategoryCreate,
    CategoryNode,
    CategoryRead,
    CategorySummary,
    CategoryUpdate,
)
from app.schemas.common import Page
from app.services.category import CategoryService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get(
    "",
    response_model=Page[CategoryRead],
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_READ))],
)
async def list_categories(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120, description="Name or slug")] = None,
    is_active: Annotated[bool | None, Query()] = None,
    parent_id: Annotated[
        uuid.UUID | None, Query(description="Direct children of this parent")
    ] = None,
    top_level: Annotated[bool | None, Query(description="Only categories with no parent")] = None,
    sort: Annotated[str | None, Query(description="e.g. name, -created_at")] = None,
) -> Page[CategoryRead]:
    categories, total = await CategoryService(session).list_categories(
        params,
        search=search,
        is_active=is_active,
        parent_id=parent_id,
        top_level=top_level,
        sort=parse_sort(sort, CategoryRepository.SORTABLE, default="name"),
    )
    return Page.build(
        [CategoryRead.model_validate(category) for category in categories],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/tree",
    response_model=list[CategoryNode],
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_READ))],
)
async def category_tree(session: SessionDep) -> list[CategoryNode]:
    """The full category hierarchy, nested for management screens and pickers."""
    return await CategoryService(session).tree()


@router.get(
    "/options",
    response_model=list[CategorySummary],
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_READ))],
)
async def category_options(session: SessionDep) -> list[CategorySummary]:
    """Lightweight active-only list for pickers."""
    categories = await CategoryService(session).list_all()
    return [CategorySummary.model_validate(category) for category in categories]


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_WRITE))],
)
async def create_category(session: SessionDep, payload: CategoryCreate) -> CategoryRead:
    return CategoryRead.model_validate(await CategoryService(session).create(payload))


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_READ))],
)
async def get_category(session: SessionDep, category_id: uuid.UUID) -> CategoryRead:
    return CategoryRead.model_validate(await CategoryService(session).get_or_404(category_id))


@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_WRITE))],
)
async def update_category(
    session: SessionDep, category_id: uuid.UUID, payload: CategoryUpdate
) -> CategoryRead:
    return CategoryRead.model_validate(await CategoryService(session).update(category_id, payload))


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_DELETE))],
)
async def delete_category(session: SessionDep, category_id: uuid.UUID) -> None:
    await CategoryService(session).delete(category_id)
