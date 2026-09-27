"""Inventory endpoints: stock levels, the movement ledger and adjustments.

Reads need ``inventory:read``. Recording a movement needs ``inventory:adjust``
and is the only way stock changes through the API.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.stock_level import StockLevelRepository
from app.repositories.stock_movement import StockMovementRepository
from app.schemas.common import Page
from app.schemas.inventory import (
    InventorySummary,
    MovementCreate,
    MovementRead,
    MovementType,
    ReferenceType,
    StockLevelRead,
)
from app.services.inventory import InventoryService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/inventory", tags=["inventory"])

StockFilter = Literal["in_stock", "low_stock", "out_of_stock"]


@router.get(
    "/stock",
    response_model=Page[StockLevelRead],
    dependencies=[Depends(require_permissions(PermissionCode.INVENTORY_READ))],
)
async def list_stock(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120, description="Name, SKU or barcode")] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    stock_status: Annotated[StockFilter | None, Query(alias="status")] = None,
    sort: Annotated[
        str | None, Query(description="e.g. product_name, quantity, -updated_at")
    ] = None,
) -> Page[StockLevelRead]:
    levels, total = await InventoryService(session).list_levels(
        params,
        sort=parse_sort(sort, StockLevelRepository.SORTABLE, default="product_name"),
        search=search,
        branch_id=branch_id,
        category_id=category_id,
        status=stock_status,
    )
    return Page.build(
        [StockLevelRead.model_validate(level) for level in levels],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/stock/summary",
    response_model=InventorySummary,
    dependencies=[Depends(require_permissions(PermissionCode.INVENTORY_READ))],
)
async def stock_summary(
    session: SessionDep,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
) -> InventorySummary:
    """Counts that drive the low-stock and out-of-stock views."""
    data = await InventoryService(session).summary(branch_id=branch_id)
    return InventorySummary.model_validate(data)


@router.get(
    "/movements",
    response_model=Page[MovementRead],
    dependencies=[Depends(require_permissions(PermissionCode.INVENTORY_READ))],
)
async def list_movements(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120, description="Name, SKU or barcode")] = None,
    product_id: Annotated[uuid.UUID | None, Query()] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    movement_type: Annotated[MovementType | None, Query()] = None,
    reference_type: Annotated[ReferenceType | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. created_at, -created_at")] = None,
) -> Page[MovementRead]:
    movements, total = await InventoryService(session).list_movements(
        params,
        sort=parse_sort(sort, StockMovementRepository.SORTABLE, default="-created_at"),
        search=search,
        product_id=product_id,
        branch_id=branch_id,
        movement_type=movement_type,
        reference_type=reference_type,
    )
    return Page.build(
        [MovementRead.model_validate(movement) for movement in movements],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "/movements",
    response_model=MovementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a stock movement",
    dependencies=[Depends(require_permissions(PermissionCode.INVENTORY_ADJUST))],
)
async def create_movement(
    session: SessionDep, actor: CurrentUser, payload: MovementCreate
) -> MovementRead:
    movement = await InventoryService(session).record_movement(
        product_id=payload.product_id,
        branch_id=payload.branch_id,
        quantity=payload.quantity,
        movement_type=payload.movement_type,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        user_id=actor.id,
        note=payload.note,
    )
    return MovementRead.model_validate(movement)
