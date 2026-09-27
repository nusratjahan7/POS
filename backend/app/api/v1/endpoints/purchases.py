"""Purchase endpoints.

Raising a purchase never touches stock. ``POST /purchases/{id}/receive`` is the
only operation that does — and it does so atomically (see ``PurchaseService.receive``).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.purchase import PurchaseRepository
from app.schemas.common import Page
from app.schemas.purchase import (
    PurchaseCreate,
    PurchaseRead,
    PurchaseStatus,
    PurchaseSummary,
    PurchaseUpdate,
)
from app.services.purchase import PurchaseService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.get(
    "",
    response_model=Page[PurchaseSummary],
    dependencies=[Depends(require_permissions(PermissionCode.PURCHASES_VIEW))],
)
async def list_purchases(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=32, description="Purchase number")] = None,
    supplier_id: Annotated[uuid.UUID | None, Query()] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    purchase_status: Annotated[PurchaseStatus | None, Query(alias="status")] = None,
    date_from: Annotated[date | None, Query(description="Purchase date on or after")] = None,
    date_to: Annotated[date | None, Query(description="Purchase date on or before")] = None,
    sort: Annotated[str | None, Query(description="e.g. -created_at, -total")] = None,
) -> Page[PurchaseSummary]:
    purchases, total = await PurchaseService(session).list_purchases(
        params,
        sort=parse_sort(sort, PurchaseRepository.SORTABLE, default="-created_at"),
        search=search,
        supplier_id=supplier_id,
        branch_id=branch_id,
        status=purchase_status,
        date_from=date_from,
        date_to=date_to,
    )
    return Page.build(
        [PurchaseSummary.model_validate(purchase) for purchase in purchases],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "",
    response_model=PurchaseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.PURCHASES_CREATE))],
)
async def create_purchase(
    session: SessionDep, actor: CurrentUser, payload: PurchaseCreate
) -> PurchaseRead:
    purchase = await PurchaseService(session).create(payload, actor_id=actor.id)
    return PurchaseRead.model_validate(purchase)


@router.get(
    "/{purchase_id}",
    response_model=PurchaseRead,
    dependencies=[Depends(require_permissions(PermissionCode.PURCHASES_VIEW))],
)
async def get_purchase(session: SessionDep, purchase_id: uuid.UUID) -> PurchaseRead:
    return PurchaseRead.model_validate(await PurchaseService(session).get_or_404(purchase_id))


@router.patch(
    "/{purchase_id}",
    response_model=PurchaseRead,
    dependencies=[Depends(require_permissions(PermissionCode.PURCHASES_UPDATE))],
)
async def update_purchase(
    session: SessionDep, purchase_id: uuid.UUID, payload: PurchaseUpdate
) -> PurchaseRead:
    return PurchaseRead.model_validate(await PurchaseService(session).update(purchase_id, payload))


@router.post(
    "/{purchase_id}/receive",
    response_model=PurchaseRead,
    summary="Receive a purchase (moves stock)",
    dependencies=[Depends(require_permissions(PermissionCode.PURCHASES_UPDATE))],
)
async def receive_purchase(
    session: SessionDep, actor: CurrentUser, purchase_id: uuid.UUID
) -> PurchaseRead:
    return PurchaseRead.model_validate(
        await PurchaseService(session).receive(purchase_id, actor_id=actor.id)
    )


@router.post(
    "/{purchase_id}/cancel",
    response_model=PurchaseRead,
    dependencies=[Depends(require_permissions(PermissionCode.PURCHASES_UPDATE))],
)
async def cancel_purchase(session: SessionDep, purchase_id: uuid.UUID) -> PurchaseRead:
    return PurchaseRead.model_validate(await PurchaseService(session).cancel(purchase_id))


@router.delete(
    "/{purchase_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.PURCHASES_UPDATE))],
)
async def delete_purchase(session: SessionDep, purchase_id: uuid.UUID) -> None:
    await PurchaseService(session).delete(purchase_id)
