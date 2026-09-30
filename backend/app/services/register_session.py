"""Cash register sessions: opening a till, tracking its drawer and closing it.

Every cash event during a shift is a :class:`CashMovement` against the session, so
the expected drawer is always ``opening_cash + Σ movements``. Other modules record
their own movements through :meth:`RegisterSessionService.record_cash`, which —
like ``InventoryService.apply_movement`` — never commits: the caller owns the
transaction so the movement lands with the sale/return/expense that caused it.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.cash_movement import CashMovement
from app.models.register import Register
from app.models.register_session import RegisterSession
from app.repositories.register import RegisterRepository
from app.repositories.register_session import RegisterSessionRepository
from app.schemas.register_session import (
    CashAdjustment,
    CashMovementRead,
    RegisterSessionClose,
    RegisterSessionDetail,
    RegisterSessionOpen,
    RegisterSessionRead,
    SessionSummary,
)
from app.utils.money import ZERO, money
from app.utils.pagination import PageParams


class RegisterSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sessions = RegisterSessionRepository(session)
        self.registers = RegisterRepository(session)

    # --- Reads -------------------------------------------------------------
    async def get_or_404(self, session_id: uuid.UUID) -> RegisterSession:
        record = await self.sessions.get_detailed(session_id)
        if record is None:
            raise NotFoundError("Register session not found.", code="register_session_not_found")
        return record

    async def current(self, register_id: uuid.UUID) -> RegisterSession | None:
        await self._register_or_404(register_id)
        return await self.sessions.get_open_for_register(register_id)

    async def list_open(self, *, branch_id: uuid.UUID | None = None) -> Sequence[RegisterSession]:
        return await self.sessions.list_open(branch_id=branch_id)

    async def list_sessions(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[RegisterSession], int]:
        return await self.sessions.list_sessions(params, sort=sort, **filters)

    async def detail(self, session_id: uuid.UUID) -> RegisterSessionDetail:
        record = await self.get_or_404(session_id)
        return RegisterSessionDetail(session=self.read(record), summary=self.summary(record))

    # --- Presentation helpers ---------------------------------------------
    @staticmethod
    def expected_cash(record: RegisterSession) -> Decimal:
        """``opening_cash + Σ movements`` — the drawer's reconciled figure."""
        if record.status == "closed" and record.expected_cash is not None:
            return Decimal(record.expected_cash)
        return money(record.opening_cash + RegisterSessionService._sum(record))

    @staticmethod
    def _sum(record: RegisterSession) -> Decimal:
        return sum((Decimal(m.amount) for m in record.movements), ZERO)

    @classmethod
    def read(cls, record: RegisterSession) -> RegisterSessionRead:
        data = RegisterSessionRead.model_validate(record)
        # While open, expected cash is live from the ledger; once closed it is stored.
        return data.model_copy(update={"expected_cash": cls.expected_cash(record)})

    @classmethod
    def summary(cls, record: RegisterSession) -> SessionSummary:
        by_type: dict[str, Decimal] = {}
        for movement in record.movements:
            by_type[movement.movement_type] = by_type.get(movement.movement_type, ZERO) + Decimal(
                movement.amount
            )

        cash_sales = by_type.get("sale", ZERO)
        # Refunds, expenses and cash-outs are stored negative; show magnitudes.
        cash_refunds = -by_type.get("refund", ZERO)
        cash_expenses = -by_type.get("expense", ZERO)
        cash_in = by_type.get("cash_in", ZERO)
        cash_out = -by_type.get("cash_out", ZERO)
        expected = money(
            Decimal(record.opening_cash)
            + cash_sales
            - cash_refunds
            - cash_expenses
            + cash_in
            - cash_out
        )
        return SessionSummary(
            opening_cash=record.opening_cash,
            cash_sales=cash_sales,
            cash_refunds=cash_refunds,
            cash_expenses=cash_expenses,
            cash_in=cash_in,
            cash_out=cash_out,
            expected_cash=expected,
            movements=[CashMovementRead.model_validate(m) for m in record.movements],
        )

    # --- Commands ----------------------------------------------------------
    async def open(
        self, payload: RegisterSessionOpen, *, actor_id: uuid.UUID | None = None
    ) -> RegisterSession:
        register = await self._register_or_404(payload.register_id)
        if not register.is_active:
            raise UnprocessableError(
                "That register is inactive.", code="register_inactive"
            )
        if await self.sessions.get_open_for_register(register.id) is not None:
            raise ConflictError(
                "This register already has an open session — close it first.",
                code="register_already_open",
            )

        opening_cash = money(payload.opening_cash)
        if register.require_opening_balance and opening_cash <= 0:
            raise UnprocessableError(
                "An opening cash amount is required to open this register.",
                code="opening_balance_required",
                details=[{"field": "opening_cash", "message": "Must be greater than zero."}],
            )
        if (
            not register.allow_opening_balance_override
            and opening_cash != register.default_opening_balance
        ):
            raise UnprocessableError(
                f"This register opens with a fixed float of {register.default_opening_balance}.",
                code="opening_balance_override_denied",
                details=[{"field": "opening_cash", "message": "Override not allowed."}],
            )

        session = RegisterSession(
            register_id=register.id,
            branch_id=register.branch_id,
            opening_cash=opening_cash,
            status="open",
            opened_by_id=actor_id,
        )
        self.session.add(session)
        await self.session.commit()
        return await self.get_or_404(session.id)

    async def close(
        self,
        session_id: uuid.UUID,
        payload: RegisterSessionClose,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> RegisterSession:
        record = await self.get_or_404(session_id)
        if record.status != "open":
            raise ConflictError(
                "This register session is already closed.", code="session_not_open"
            )

        expected = self.expected_cash(record)
        actual = money(payload.actual_cash)
        record.expected_cash = expected
        record.actual_cash = actual
        record.difference = money(actual - expected)
        record.closing_note = (payload.note or "").strip() or None
        record.status = "closed"
        record.closed_by_id = actor_id
        record.closed_at = datetime.now(UTC)

        await self.session.commit()
        return await self.get_or_404(session_id)

    async def adjust(
        self,
        session_id: uuid.UUID,
        payload: CashAdjustment,
        *,
        movement_type: str,
        actor_id: uuid.UUID | None = None,
    ) -> RegisterSession:
        """Move cash in (`cash_in`) or out (`cash_out`) of an open drawer."""
        record = await self.get_or_404(session_id)
        if record.status != "open":
            raise ConflictError(
                "This register session is closed.", code="session_not_open"
            )
        signed = money(payload.amount) if movement_type == "cash_in" else -money(payload.amount)
        await self.record_cash(
            record.id,
            signed,
            movement_type=movement_type,
            reference_type="manual",
            user_id=actor_id,
            note=payload.note,
        )
        await self.session.commit()
        return await self.get_or_404(session_id)

    async def require_open(self, register_id: uuid.UUID) -> RegisterSession:
        """The open session a sale must be rung against."""
        register = await self._register_or_404(register_id)
        if not register.is_active:
            raise UnprocessableError("That register is inactive.", code="register_inactive")
        session = await self.sessions.get_open_for_register(register.id)
        if session is None:
            raise ConflictError(
                "Open the register before ringing a sale.", code="register_not_open"
            )
        return session

    async def record_cash(
        self,
        session_id: uuid.UUID,
        amount: Decimal,
        *,
        movement_type: str,
        reference_type: str = "manual",
        reference_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        note: str | None = None,
    ) -> None:
        """Stage a signed cash movement. Does **not** commit — the caller owns it."""
        if amount == 0:
            return
        self.session.add(
            CashMovement(
                session_id=session_id,
                movement_type=movement_type,
                amount=money(amount),
                reference_type=reference_type,
                reference_id=reference_id,
                note=note,
                user_id=user_id,
            )
        )

    # --- Internals ---------------------------------------------------------
    async def _register_or_404(self, register_id: uuid.UUID) -> Register:
        register = await self.registers.get(register_id)
        if register is None or register.is_deleted:
            raise NotFoundError("Register not found.", code="register_not_found")
        return register
