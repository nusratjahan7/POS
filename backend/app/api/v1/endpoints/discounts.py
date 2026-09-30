"""Discount and coupon endpoints: management, plus the till's pricing preview."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.discount import DiscountRepository
from app.schemas.common import Page
from app.schemas.discount import (
    DiscountCreate,
    DiscountPreviewRequest,
    DiscountRead,
    DiscountUpdate,
    PriceBreakdown,
)
from app.services.discount import DiscountService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/discounts", tags=["discounts"])


@router.get(
    "",
    response_model=Page[DiscountRead],
    dependencies=[Depends(require_permissions(PermissionCode.DISCOUNTS_READ))],
)
async def list_discounts(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120, description="Name or code")] = None,
    scope: Annotated[str | None, Query(description="product | cart")] = None,
    is_active: Annotated[bool | None, Query()] = None,
    coupons_only: Annotated[bool | None, Query(description="Only coded coupons")] = None,
    sort: Annotated[str | None, Query(description="e.g. name, -value")] = None,
) -> Page[DiscountRead]:
    service = DiscountService(session)
    discounts, total = await service.list_discounts(
        params,
        sort=parse_sort(sort, DiscountRepository.SORTABLE, default="name"),
        search=search,
        scope=scope,
        is_active=is_active,
        coupons_only=coupons_only,
    )
    counts = await service.redemptions.counts_for_discounts([d.id for d in discounts])
    return Page.build(
        [
            service.read(discount, redeemed_count=counts.get(discount.id, 0))
            for discount in discounts
        ],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "/validate",
    response_model=PriceBreakdown,
    summary="Preview a basket's discounts (never persists anything)",
    dependencies=[Depends(require_permissions(PermissionCode.SALES_CREATE))],
)
async def validate_basket(
    session: SessionDep, payload: DiscountPreviewRequest
) -> PriceBreakdown:
    pricing = await DiscountService(session).price(
        payload.items,
        customer_id=payload.customer_id,
        coupon_code=payload.coupon_code,
        order_discount=payload.order_discount,
    )
    return pricing.breakdown()


@router.post(
    "",
    response_model=DiscountRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.DISCOUNTS_WRITE))],
)
async def create_discount(session: SessionDep, payload: DiscountCreate) -> DiscountRead:
    service = DiscountService(session)
    discount = await service.create(payload)
    return service.read(discount)


@router.get(
    "/{discount_id}",
    response_model=DiscountRead,
    dependencies=[Depends(require_permissions(PermissionCode.DISCOUNTS_READ))],
)
async def get_discount(session: SessionDep, discount_id: uuid.UUID) -> DiscountRead:
    service = DiscountService(session)
    discount = await service.get_or_404(discount_id)
    redeemed = await service.redemptions.count_for_discount(discount.id)
    return service.read(discount, redeemed_count=redeemed)


@router.patch(
    "/{discount_id}",
    response_model=DiscountRead,
    dependencies=[Depends(require_permissions(PermissionCode.DISCOUNTS_WRITE))],
)
async def update_discount(
    session: SessionDep, discount_id: uuid.UUID, payload: DiscountUpdate
) -> DiscountRead:
    service = DiscountService(session)
    discount = await service.update(discount_id, payload)
    return service.read(discount)


@router.delete(
    "/{discount_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.DISCOUNTS_WRITE))],
)
async def delete_discount(session: SessionDep, discount_id: uuid.UUID) -> None:
    await DiscountService(session).delete(discount_id)
