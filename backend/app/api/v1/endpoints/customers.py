"""Customer endpoints: profile, receivables, payments and (future) purchase history."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.customer import CustomerRepository
from app.schemas.common import Page
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetails,
    CustomerPaymentCreate,
    CustomerPaymentRead,
    CustomerPurchaseRead,
    CustomerRead,
    CustomerSummary,
    CustomerUpdate,
)
from app.services.customer import CustomerService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get(
    "",
    response_model=Page[CustomerRead],
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_READ))],
)
async def list_customers(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=160, description="Name, phone or email")] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. name, -balance")] = None,
) -> Page[CustomerRead]:
    customers, total = await CustomerService(session).list_customers(
        params,
        search=search,
        is_active=is_active,
        sort=parse_sort(sort, CustomerRepository.SORTABLE, default="name"),
    )
    return Page.build(
        [CustomerRead.model_validate(customer) for customer in customers],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/options",
    response_model=list[CustomerSummary],
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_READ))],
)
async def customer_options(session: SessionDep) -> list[CustomerSummary]:
    """Lightweight active-only list for pickers (e.g. attaching a customer to a sale)."""
    customers = await CustomerService(session).list_all()
    return [CustomerSummary.model_validate(customer) for customer in customers]


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_WRITE))],
)
async def create_customer(session: SessionDep, payload: CustomerCreate) -> CustomerRead:
    return CustomerRead.model_validate(await CustomerService(session).create(payload))


@router.get(
    "/{customer_id}",
    response_model=CustomerRead,
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_READ))],
)
async def get_customer(session: SessionDep, customer_id: uuid.UUID) -> CustomerRead:
    return CustomerRead.model_validate(await CustomerService(session).get_or_404(customer_id))


@router.patch(
    "/{customer_id}",
    response_model=CustomerRead,
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_WRITE))],
)
async def update_customer(
    session: SessionDep, customer_id: uuid.UUID, payload: CustomerUpdate
) -> CustomerRead:
    return CustomerRead.model_validate(await CustomerService(session).update(customer_id, payload))


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a customer",
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_WRITE))],
)
async def deactivate_customer(session: SessionDep, customer_id: uuid.UUID) -> None:
    await CustomerService(session).deactivate(customer_id)


@router.get(
    "/{customer_id}/details",
    response_model=CustomerDetails,
    summary="Customer aggregates, recent payments and purchase history",
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_READ))],
)
async def customer_details(session: SessionDep, customer_id: uuid.UUID) -> CustomerDetails:
    data = await CustomerService(session).details(customer_id)
    return CustomerDetails(
        customer=CustomerRead.model_validate(data["customer"]),
        total_orders=data["total_orders"],
        total_purchase_amount=data["total_purchase_amount"],
        total_paid=data["total_paid"],
        outstanding_due=data["outstanding_due"],
        recent_payments=[
            CustomerPaymentRead.model_validate(payment) for payment in data["recent_payments"]
        ],
        recent_purchases=[
            CustomerPurchaseRead.model_validate(purchase) for purchase in data["recent_purchases"]
        ],
    )


@router.get(
    "/{customer_id}/payments",
    response_model=Page[CustomerPaymentRead],
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_READ))],
)
async def list_customer_payments(
    session: SessionDep, params: Pagination, customer_id: uuid.UUID
) -> Page[CustomerPaymentRead]:
    payments, total = await CustomerService(session).list_payments(customer_id, params)
    return Page.build(
        [CustomerPaymentRead.model_validate(payment) for payment in payments],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "/{customer_id}/payments",
    response_model=CustomerPaymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a payment received from a customer",
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_WRITE))],
)
async def record_customer_payment(
    session: SessionDep, actor: CurrentUser, customer_id: uuid.UUID, payload: CustomerPaymentCreate
) -> CustomerPaymentRead:
    payment = await CustomerService(session).record_payment(customer_id, payload, actor_id=actor.id)
    return CustomerPaymentRead.model_validate(payment)


@router.get(
    "/{customer_id}/purchases",
    response_model=list[CustomerPurchaseRead],
    summary="Purchase history (populated once the sales module ships)",
    dependencies=[Depends(require_permissions(PermissionCode.CUSTOMERS_READ))],
)
async def list_customer_purchases(
    session: SessionDep, customer_id: uuid.UUID
) -> list[CustomerPurchaseRead]:
    await CustomerService(session).get_or_404(customer_id)
    # No sales table yet — the shape is final, only the data is pending.
    return []
