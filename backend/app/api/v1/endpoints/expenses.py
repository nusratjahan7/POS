"""Expense endpoints: the spend ledger and its categories."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.expense import ExpenseRepository
from app.repositories.expense_category import ExpenseCategoryRepository
from app.schemas.common import Page
from app.schemas.expense import (
    ExpenseCategoryCreate,
    ExpenseCategoryRead,
    ExpenseCategorySummary,
    ExpenseCategoryUpdate,
    ExpenseCreate,
    ExpenseRead,
    ExpenseTotal,
)
from app.services.expense import ExpenseService
from app.services.expense_category import ExpenseCategoryService
from app.utils.sorting import parse_sort

router = APIRouter(tags=["expenses"])


# --- Categories ------------------------------------------------------------
@router.get(
    "/expense-categories",
    response_model=Page[ExpenseCategoryRead],
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_READ))],
)
async def list_expense_categories(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=80)] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. name")] = None,
) -> Page[ExpenseCategoryRead]:
    categories, total = await ExpenseCategoryService(session).list_categories(
        params,
        search=search,
        is_active=is_active,
        sort=parse_sort(sort, ExpenseCategoryRepository.SORTABLE, default="name"),
    )
    return Page.build(
        [ExpenseCategoryRead.model_validate(category) for category in categories],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/expense-categories/options",
    response_model=list[ExpenseCategorySummary],
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_READ))],
)
async def expense_category_options(session: SessionDep) -> list[ExpenseCategorySummary]:
    categories = await ExpenseCategoryService(session).list_all()
    return [ExpenseCategorySummary.model_validate(category) for category in categories]


@router.post(
    "/expense-categories",
    response_model=ExpenseCategoryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_WRITE))],
)
async def create_expense_category(
    session: SessionDep, payload: ExpenseCategoryCreate
) -> ExpenseCategoryRead:
    return ExpenseCategoryRead.model_validate(
        await ExpenseCategoryService(session).create(payload)
    )


@router.patch(
    "/expense-categories/{category_id}",
    response_model=ExpenseCategoryRead,
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_WRITE))],
)
async def update_expense_category(
    session: SessionDep, category_id: uuid.UUID, payload: ExpenseCategoryUpdate
) -> ExpenseCategoryRead:
    return ExpenseCategoryRead.model_validate(
        await ExpenseCategoryService(session).update(category_id, payload)
    )


@router.delete(
    "/expense-categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_WRITE))],
)
async def delete_expense_category(session: SessionDep, category_id: uuid.UUID) -> None:
    await ExpenseCategoryService(session).delete(category_id)


# --- Expenses --------------------------------------------------------------
@router.get(
    "/expenses",
    response_model=Page[ExpenseRead],
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_READ))],
)
async def list_expenses(
    session: SessionDep,
    params: Pagination,
    search: Annotated[
        str | None, Query(max_length=160, description="Description or reference")
    ] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    payment_method_id: Annotated[uuid.UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query(description="Spent on or after")] = None,
    date_to: Annotated[date | None, Query(description="Spent on or before")] = None,
    sort: Annotated[str | None, Query(description="e.g. -spent_at, -amount")] = None,
) -> Page[ExpenseRead]:
    expenses, total = await ExpenseService(session).list_expenses(
        params,
        sort=parse_sort(sort, ExpenseRepository.SORTABLE, default="-spent_at"),
        search=search,
        branch_id=branch_id,
        category_id=category_id,
        payment_method_id=payment_method_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Page.build(
        [ExpenseRead.model_validate(expense) for expense in expenses],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/expenses/summary",
    response_model=ExpenseTotal,
    summary="Total spend for the current filters",
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_READ))],
)
async def expenses_total(
    session: SessionDep,
    search: Annotated[str | None, Query(max_length=160)] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    payment_method_id: Annotated[uuid.UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> ExpenseTotal:
    amount = await ExpenseService(session).total(
        search=search,
        branch_id=branch_id,
        category_id=category_id,
        payment_method_id=payment_method_id,
        date_from=date_from,
        date_to=date_to,
    )
    return ExpenseTotal(amount=amount)


@router.post(
    "/expenses",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_WRITE))],
)
async def create_expense(
    session: SessionDep, actor: CurrentUser, payload: ExpenseCreate
) -> ExpenseRead:
    expense = await ExpenseService(session).create(payload, actor_id=actor.id)
    return ExpenseRead.model_validate(expense)


@router.get(
    "/expenses/{expense_id}",
    response_model=ExpenseRead,
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_READ))],
)
async def get_expense(session: SessionDep, expense_id: uuid.UUID) -> ExpenseRead:
    return ExpenseRead.model_validate(await ExpenseService(session).get_or_404(expense_id))


@router.delete(
    "/expenses/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.EXPENSES_WRITE))],
)
async def delete_expense(session: SessionDep, expense_id: uuid.UUID) -> None:
    await ExpenseService(session).delete(expense_id)
