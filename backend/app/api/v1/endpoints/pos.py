"""Point-of-sale endpoints — the till's product feed.

Gated on ``sales:create`` rather than ``catalog:read``: a Cashier may ring up
sales without being granted access to the catalogue administration screens. The
response deliberately omits cost fields.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.schemas.common import Page
from app.schemas.pos import PosCategory, PosProduct, PosStock
from app.services.pos import PosService

router = APIRouter(prefix="/pos", tags=["pos"])


@router.get(
    "/catalog",
    response_model=Page[PosProduct],
    summary="Sellable products for the till, with stock at a branch",
    dependencies=[Depends(require_permissions(PermissionCode.SALES_CREATE))],
)
async def pos_catalog(
    session: SessionDep,
    actor: CurrentUser,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120, description="Name, SKU or barcode")] = None,
    sku: Annotated[str | None, Query(max_length=64, description="Exact SKU")] = None,
    barcode: Annotated[str | None, Query(max_length=64, description="Exact barcode")] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    branch_id: Annotated[uuid.UUID | None, Query(description="Defaults to your branch")] = None,
) -> Page[PosProduct]:
    service = PosService(session)
    resolved_branch = await service.resolve_branch_id(branch_id, fallback=actor.branch_id)
    items, total = await service.catalog(
        params,
        branch_id=resolved_branch,
        search=search,
        sku=sku,
        barcode=barcode,
        category_id=category_id,
    )
    return Page.build(
        [PosProduct(**row) for row in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/categories",
    response_model=list[PosCategory],
    summary="Categories with product counts, for the till's filter chips",
    dependencies=[Depends(require_permissions(PermissionCode.SALES_CREATE))],
)
async def pos_categories(session: SessionDep) -> list[PosCategory]:
    rows = await PosService(session).categories()
    return [PosCategory(**row) for row in rows]


@router.get(
    "/stock",
    response_model=list[PosStock],
    summary="On-hand stock for a set of products at a branch (the cart cap)",
    dependencies=[Depends(require_permissions(PermissionCode.SALES_CREATE))],
)
async def pos_stock(
    session: SessionDep,
    actor: CurrentUser,
    branch_id: Annotated[uuid.UUID | None, Query(description="Defaults to your branch")] = None,
    ids: Annotated[list[uuid.UUID] | None, Query(description="Repeat once per product")] = None,
) -> list[PosStock]:
    service = PosService(session)
    resolved_branch = await service.resolve_branch_id(branch_id, fallback=actor.branch_id)
    rows = await service.stock_for(resolved_branch, ids or [])
    return [PosStock(**row) for row in rows]
