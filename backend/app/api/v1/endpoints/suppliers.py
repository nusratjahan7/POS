"""Supplier endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.supplier import SupplierRepository
from app.schemas.common import Page
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierSummary, SupplierUpdate
from app.services.supplier import SupplierService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get(
    "",
    response_model=Page[SupplierRead],
    dependencies=[Depends(require_permissions(PermissionCode.SUPPLIERS_READ))],
)
async def list_suppliers(
    session: SessionDep,
    params: Pagination,
    search: Annotated[
        str | None, Query(max_length=160, description="Name, company or phone")
    ] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. name, -balance")] = None,
) -> Page[SupplierRead]:
    suppliers, total = await SupplierService(session).list_suppliers(
        params,
        search=search,
        is_active=is_active,
        sort=parse_sort(sort, SupplierRepository.SORTABLE, default="name"),
    )
    return Page.build(
        [SupplierRead.model_validate(supplier) for supplier in suppliers],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/options",
    response_model=list[SupplierSummary],
    dependencies=[Depends(require_permissions(PermissionCode.SUPPLIERS_READ))],
)
async def supplier_options(session: SessionDep) -> list[SupplierSummary]:
    """Lightweight active-only list for pickers (e.g. the purchase form)."""
    suppliers = await SupplierService(session).list_all()
    return [SupplierSummary.model_validate(supplier) for supplier in suppliers]


@router.post(
    "",
    response_model=SupplierRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.SUPPLIERS_WRITE))],
)
async def create_supplier(session: SessionDep, payload: SupplierCreate) -> SupplierRead:
    return SupplierRead.model_validate(await SupplierService(session).create(payload))


@router.get(
    "/{supplier_id}",
    response_model=SupplierRead,
    dependencies=[Depends(require_permissions(PermissionCode.SUPPLIERS_READ))],
)
async def get_supplier(session: SessionDep, supplier_id: uuid.UUID) -> SupplierRead:
    return SupplierRead.model_validate(await SupplierService(session).get_or_404(supplier_id))


@router.patch(
    "/{supplier_id}",
    response_model=SupplierRead,
    dependencies=[Depends(require_permissions(PermissionCode.SUPPLIERS_WRITE))],
)
async def update_supplier(
    session: SessionDep, supplier_id: uuid.UUID, payload: SupplierUpdate
) -> SupplierRead:
    return SupplierRead.model_validate(await SupplierService(session).update(supplier_id, payload))


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.SUPPLIERS_WRITE))],
)
async def delete_supplier(session: SessionDep, supplier_id: uuid.UUID) -> None:
    await SupplierService(session).delete(supplier_id)
