"""Expenses: what the business spends, and the drawer it came out of.

A cash expense must name the register session it was paid from, and posts a
negative cash movement there, so closing the till reconciles money that actually
left the drawer. Non-cash expenses touch no drawer.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.expense import Expense
from app.repositories.branch import BranchRepository
from app.repositories.cash_movement import CashMovementRepository
from app.repositories.expense import ExpenseRepository
from app.repositories.expense_category import ExpenseCategoryRepository
from app.repositories.payment_method import PaymentMethodRepository
from app.repositories.register_session import RegisterSessionRepository
from app.schemas.expense import ExpenseCreate
from app.services.register_session import RegisterSessionService
from app.utils.money import money
from app.utils.pagination import PageParams


class ExpenseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.expenses = ExpenseRepository(session)
        self.branches = BranchRepository(session)
        self.categories = ExpenseCategoryRepository(session)
        self.methods = PaymentMethodRepository(session)
        self.sessions = RegisterSessionRepository(session)
        self.movements = CashMovementRepository(session)
        self.cash = RegisterSessionService(session)

    # --- Reads -------------------------------------------------------------
    async def get_or_404(self, expense_id: uuid.UUID) -> Expense:
        expense = (
            (await self.session.execute(select(Expense).where(Expense.id == expense_id)))
            .scalars()
            .one_or_none()
        )
        if expense is None:
            raise NotFoundError("Expense not found.", code="expense_not_found")
        return expense

    async def list_expenses(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Expense], int]:
        return await self.expenses.list_expenses(params, sort=sort, **filters)

    async def total(self, **filters: Any) -> Decimal:
        return await self.expenses.sum_amount(**filters)

    # --- Commands ----------------------------------------------------------
    async def create(
        self, payload: ExpenseCreate, *, actor_id: uuid.UUID | None = None
    ) -> Expense:
        branch = await self.branches.get(payload.branch_id)
        if branch is None or branch.is_deleted:
            raise UnprocessableError(
                "The selected branch does not exist.",
                code="unknown_branch",
                details=[{"field": "branch_id", "message": "Unknown branch."}],
            )
        category = await self.categories.get(payload.category_id)
        if category is None or category.is_deleted:
            raise UnprocessableError(
                "The selected category does not exist.",
                code="unknown_expense_category",
                details=[{"field": "category_id", "message": "Unknown category."}],
            )
        method = await self.methods.get(payload.payment_method_id)
        if method is None or method.is_deleted or not method.is_active:
            raise UnprocessableError(
                "That payment method is not available.",
                code="unknown_payment_method",
                details=[{"field": "payment_method_id", "message": "Unavailable method."}],
            )

        session_id: uuid.UUID | None = None
        if method.opens_cash_drawer:
            session_id = await self._resolve_cash_session(payload, branch.id)

        expense = Expense(
            branch_id=branch.id,
            category_id=category.id,
            payment_method_id=method.id,
            register_session_id=session_id,
            amount=money(payload.amount),
            description=(payload.description or "").strip() or None,
            reference=(payload.reference or "").strip() or None,
            spent_at=payload.spent_at,
            created_by_id=actor_id,
        )
        await self.expenses.add(expense)

        if session_id is not None:
            await self.cash.record_cash(
                session_id,
                -money(payload.amount),
                movement_type="expense",
                reference_type="expense",
                reference_id=expense.id,
                user_id=actor_id,
                note=f"Expense: {category.name}",
            )

        await self.session.commit()
        return await self.get_or_404(expense.id)

    async def delete(self, expense_id: uuid.UUID) -> None:
        """Remove an expense, reversing its drawer movement while the till is open."""
        expense = await self.get_or_404(expense_id)
        if expense.register_session_id is not None:
            session = await self.sessions.get_detailed(expense.register_session_id)
            if session is not None and session.status != "open":
                raise ConflictError(
                    "This expense is on a closed register session and cannot be removed.",
                    code="expense_locked",
                )
            await self.movements.delete_for_reference("expense", expense.id)
        await self.expenses.delete(expense)
        await self.session.commit()

    # --- Internals ---------------------------------------------------------
    async def _resolve_cash_session(
        self, payload: ExpenseCreate, branch_id: uuid.UUID
    ) -> uuid.UUID:
        if payload.register_session_id is None:
            raise UnprocessableError(
                "A cash expense needs the register session it was paid from.",
                code="expense_session_required",
                details=[{"field": "register_session_id", "message": "Required for cash."}],
            )
        session = await self.sessions.get_detailed(payload.register_session_id)
        if session is None:
            raise UnprocessableError(
                "The selected register session does not exist.",
                code="unknown_register_session",
                details=[{"field": "register_session_id", "message": "Unknown session."}],
            )
        if session.status != "open":
            raise UnprocessableError(
                "That register session is closed.",
                code="session_not_open",
                details=[{"field": "register_session_id", "message": "Already closed."}],
            )
        if session.branch_id != branch_id:
            raise UnprocessableError(
                "The register session belongs to a different branch.",
                code="session_branch_mismatch",
                details=[{"field": "register_session_id", "message": "Wrong branch."}],
            )
        return session.id
