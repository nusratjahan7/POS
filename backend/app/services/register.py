"""Register management."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.branch import Branch
from app.models.register import Register
from app.repositories.branch import BranchRepository
from app.repositories.register import RegisterRepository
from app.schemas.register import RegisterCreate, RegisterUpdate
from app.utils.pagination import PageParams


class RegisterService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.registers = RegisterRepository(session)
        self.branches = BranchRepository(session)

    async def get_or_404(self, register_id: uuid.UUID) -> Register:
        register = await self.registers.get(register_id)
        if register is None or register.is_deleted:
            raise NotFoundError("Register not found.", code="register_not_found")
        return register

    async def list_registers(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Register], int]:
        return await self.registers.list_registers(params, sort=sort, **filters)

    async def list_all(self, *, branch_id: uuid.UUID | None = None) -> Sequence[Register]:
        return await self.registers.list_all(branch_id=branch_id)

    # --- Internals ---------------------------------------------------------
    async def _resolve_branch(self, branch_id: uuid.UUID) -> Branch:
        branch = await self.branches.get(branch_id)
        if branch is None or branch.is_deleted:
            raise NotFoundError(
                "The selected branch does not exist.",
                code="unknown_branch",
            )
        return branch

    async def _assert_name_free(
        self,
        name: str,
        *,
        branch_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        if await self.registers.name_exists(name, branch_id=branch_id, exclude_id=exclude_id):
            raise ConflictError(
                "A register with that name already exists in this branch.",
                code="register_name_taken",
                details=[{"field": "name", "message": "Already in use in this branch."}],
            )

    # --- Commands ----------------------------------------------------------
    async def create(self, payload: RegisterCreate) -> Register:
        branch = await self._resolve_branch(payload.branch_id)
        await self._assert_name_free(payload.name, branch_id=branch.id)

        register = Register(
            name=payload.name.strip(),
            # Assign the relationship (not just the FK) so the response can be
            # serialised without a lazy load after the insert.
            branch=branch,
            is_active=payload.is_active,
            default_opening_balance=payload.default_opening_balance,
            require_opening_balance=payload.require_opening_balance,
            allow_opening_balance_override=payload.allow_opening_balance_override,
        )
        await self.registers.add(register)
        await self.session.commit()
        return register

    async def update(self, register_id: uuid.UUID, payload: RegisterUpdate) -> Register:
        register = await self.get_or_404(register_id)

        branch_changed = payload.branch_id is not None and payload.branch_id != register.branch_id
        target_branch_id = register.branch_id
        if branch_changed and payload.branch_id is not None:
            branch = await self._resolve_branch(payload.branch_id)
            register.branch = branch
            target_branch_id = branch.id

        if payload.name is not None:
            name = payload.name.strip()
            if name.lower() != register.name.lower() or branch_changed:
                await self._assert_name_free(
                    name, branch_id=target_branch_id, exclude_id=register.id
                )
            register.name = name

        if payload.is_active is not None:
            register.is_active = payload.is_active
        if payload.default_opening_balance is not None:
            register.default_opening_balance = payload.default_opening_balance
        if payload.require_opening_balance is not None:
            register.require_opening_balance = payload.require_opening_balance
        if payload.allow_opening_balance_override is not None:
            register.allow_opening_balance_override = payload.allow_opening_balance_override

        await self.session.commit()
        return register

    async def delete(self, register_id: uuid.UUID) -> None:
        register = await self.get_or_404(register_id)
        register.is_active = False
        register.deleted_at = datetime.now(UTC)
        await self.session.commit()
