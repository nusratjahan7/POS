"""Payment-method management."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.payment_method import PaymentMethod
from app.repositories.payment_method import PaymentMethodRepository
from app.schemas.payment_method import PaymentMethodCreate, PaymentMethodUpdate
from app.utils.pagination import PageParams
from app.utils.text import normalize_code


class PaymentMethodService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.methods = PaymentMethodRepository(session)

    async def get_or_404(self, method_id: uuid.UUID) -> PaymentMethod:
        method = await self.methods.get(method_id)
        if method is None or method.is_deleted:
            raise NotFoundError("Payment method not found.", code="payment_method_not_found")
        return method

    async def list_payment_methods(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[PaymentMethod], int]:
        return await self.methods.list_payment_methods(params, sort=sort, **filters)

    async def list_all(self, *, active_only: bool = True) -> Sequence[PaymentMethod]:
        return await self.methods.list_all(active_only=active_only)

    # --- Internals ---------------------------------------------------------
    async def _assert_code_free(self, code: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if await self.methods.code_exists(code, exclude_id=exclude_id):
            raise ConflictError(
                "A payment method with that code already exists.",
                code="payment_code_taken",
                details=[{"field": "code", "message": "Already in use."}],
            )

    async def _assert_name_free(self, name: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if await self.methods.name_exists(name, exclude_id=exclude_id):
            raise ConflictError(
                "A payment method with that name already exists.",
                code="payment_name_taken",
                details=[{"field": "name", "message": "Already in use."}],
            )

    # --- Commands ----------------------------------------------------------
    async def create(self, payload: PaymentMethodCreate) -> PaymentMethod:
        code = normalize_code(payload.code)
        name = payload.name.strip()
        await self._assert_code_free(code)
        await self._assert_name_free(name)

        method = PaymentMethod(
            name=name,
            code=code,
            kind=payload.kind,
            description=payload.description,
            is_active=payload.is_active,
            opens_cash_drawer=payload.opens_cash_drawer,
            requires_reference=payload.requires_reference,
            sort_order=payload.sort_order,
        )
        await self.methods.add(method)
        await self.session.commit()
        return method

    async def update(self, method_id: uuid.UUID, payload: PaymentMethodUpdate) -> PaymentMethod:
        method = await self.get_or_404(method_id)
        provided = payload.model_fields_set

        if payload.code is not None:
            code = normalize_code(payload.code)
            # Seeded methods keep their code: sales will reference it forever.
            if method.is_system and code != method.code:
                raise ForbiddenError(
                    "The code of a built-in payment method cannot be changed.",
                    code="payment_method_immutable",
                )
            if code != method.code:
                await self._assert_code_free(code, exclude_id=method.id)
                method.code = code

        if payload.name is not None:
            name = payload.name.strip()
            if name.lower() != method.name.lower():
                await self._assert_name_free(name, exclude_id=method.id)
                method.name = name

        if payload.kind is not None:
            method.kind = payload.kind
        if "description" in provided:
            method.description = payload.description
        if payload.is_active is not None:
            method.is_active = payload.is_active
        if payload.opens_cash_drawer is not None:
            method.opens_cash_drawer = payload.opens_cash_drawer
        if payload.requires_reference is not None:
            method.requires_reference = payload.requires_reference
        if payload.sort_order is not None:
            method.sort_order = payload.sort_order

        await self.session.commit()
        return method

    async def delete(self, method_id: uuid.UUID) -> None:
        method = await self.get_or_404(method_id)
        if method.is_system:
            raise ForbiddenError(
                "Built-in payment methods cannot be deleted. Deactivate it instead.",
                code="payment_method_immutable",
            )
        method.is_active = False
        method.deleted_at = datetime.now(UTC)
        await self.session.commit()
