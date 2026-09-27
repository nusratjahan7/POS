"""Sales endpoints.

``POST /sales`` is the transaction that completes a sale: it prices the basket
server-side, tends the payment, takes the stock out of the branch and settles any
credit — all or nothing. No other endpoint may create a sale.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.sale import SaleRepository
from app.schemas.common import Page
from app.schemas.sale import SaleCreate, SaleRead, SaleReceipt, SaleStatus, SaleSummary
from app.services.sale import SaleService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post(
    "",
    response_model=SaleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Complete a sale (prices, stock and payments in one transaction)",
    dependencies=[Depends(require_permissions(PermissionCode.SALES_CREATE))],
)
async def create_sale(session: SessionDep, actor: CurrentUser, payload: SaleCreate) -> SaleRead:
    sale = await SaleService(session).create(payload, actor_id=actor.id)
    return SaleRead.model_validate(sale)


@router.get(
    "",
    response_model=Page[SaleSummary],
    dependencies=[Depends(require_permissions(PermissionCode.SALES_READ))],
)
async def list_sales(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=32, description="Invoice number")] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    customer_id: Annotated[uuid.UUID | None, Query()] = None,
    cashier_id: Annotated[uuid.UUID | None, Query()] = None,
    sale_status: Annotated[SaleStatus | None, Query(alias="status")] = None,
    date_from: Annotated[date | None, Query(description="Sold on or after")] = None,
    date_to: Annotated[date | None, Query(description="Sold on or before")] = None,
    sort: Annotated[str | None, Query(description="e.g. -sold_at, -total")] = None,
) -> Page[SaleSummary]:
    sales, total = await SaleService(session).list_sales(
        params,
        sort=parse_sort(sort, SaleRepository.SORTABLE, default="-sold_at"),
        search=search,
        branch_id=branch_id,
        customer_id=customer_id,
        cashier_id=cashier_id,
        status=sale_status,
        date_from=date_from,
        date_to=date_to,
    )
    return Page.build(
        [SaleSummary.model_validate(sale) for sale in sales],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/{sale_id}",
    response_model=SaleRead,
    dependencies=[Depends(require_permissions(PermissionCode.SALES_READ))],
)
async def get_sale(session: SessionDep, sale_id: uuid.UUID) -> SaleRead:
    return SaleRead.model_validate(await SaleService(session).get_or_404(sale_id))


@router.get(
    "/{sale_id}/receipt",
    response_model=SaleReceipt,
    summary="A sale plus the business details a printed receipt needs",
    dependencies=[Depends(require_permissions(PermissionCode.SALES_READ))],
)
async def get_sale_receipt(session: SessionDep, sale_id: uuid.UUID) -> SaleReceipt:
    return SaleReceipt.model_validate(await SaleService(session).receipt(sale_id))
