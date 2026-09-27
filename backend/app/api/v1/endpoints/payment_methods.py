"""Payment-method endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.payment_method import PaymentMethodRepository
from app.schemas.common import Page
from app.schemas.payment_method import (
    PaymentKind,
    PaymentMethodCreate,
    PaymentMethodRead,
    PaymentMethodSummary,
    PaymentMethodUpdate,
)
from app.services.payment_method import PaymentMethodService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])


@router.get(
    "",
    response_model=Page[PaymentMethodRead],
    dependencies=[Depends(require_permissions(PermissionCode.PAYMENTS_READ))],
)
async def list_payment_methods(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120)] = None,
    kind: Annotated[PaymentKind | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. sort_order, name")] = None,
) -> Page[PaymentMethodRead]:
    methods, total = await PaymentMethodService(session).list_payment_methods(
        params,
        sort=parse_sort(sort, PaymentMethodRepository.SORTABLE, default="sort_order"),
        search=search,
        kind=kind,
        is_active=is_active,
    )
    return Page.build(
        [PaymentMethodRead.model_validate(method) for method in methods],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/options",
    response_model=list[PaymentMethodSummary],
    dependencies=[Depends(require_permissions(PermissionCode.PAYMENTS_READ))],
)
async def payment_method_options(session: SessionDep) -> list[PaymentMethodSummary]:
    """Active methods only — what a till may tender with."""
    methods = await PaymentMethodService(session).list_all(active_only=True)
    return [PaymentMethodSummary.model_validate(method) for method in methods]


@router.post(
    "",
    response_model=PaymentMethodRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.PAYMENTS_WRITE))],
)
async def create_payment_method(
    session: SessionDep, payload: PaymentMethodCreate
) -> PaymentMethodRead:
    return PaymentMethodRead.model_validate(await PaymentMethodService(session).create(payload))


@router.get(
    "/{method_id}",
    response_model=PaymentMethodRead,
    dependencies=[Depends(require_permissions(PermissionCode.PAYMENTS_READ))],
)
async def get_payment_method(session: SessionDep, method_id: uuid.UUID) -> PaymentMethodRead:
    return PaymentMethodRead.model_validate(
        await PaymentMethodService(session).get_or_404(method_id)
    )


@router.patch(
    "/{method_id}",
    response_model=PaymentMethodRead,
    dependencies=[Depends(require_permissions(PermissionCode.PAYMENTS_WRITE))],
)
async def update_payment_method(
    session: SessionDep, method_id: uuid.UUID, payload: PaymentMethodUpdate
) -> PaymentMethodRead:
    return PaymentMethodRead.model_validate(
        await PaymentMethodService(session).update(method_id, payload)
    )


@router.delete(
    "/{method_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.PAYMENTS_WRITE))],
)
async def delete_payment_method(session: SessionDep, method_id: uuid.UUID) -> None:
    await PaymentMethodService(session).delete(method_id)
