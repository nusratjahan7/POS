"""Branch management. Branches scope every future operational record."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.branch import Branch
from app.repositories.branch import BranchRepository
from app.schemas.branch import BranchCreate, BranchUpdate
from app.utils.pagination import PageParams
from app.utils.text import normalize_code


class BranchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.branches = BranchRepository(session)

    async def get_or_404(self, branch_id: uuid.UUID) -> Branch:
        branch = await self.branches.get(branch_id)
        if branch is None or branch.is_deleted:
            raise NotFoundError("Branch not found.", code="branch_not_found")
        return branch

    async def list_branches(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Branch], int]:
        return await self.branches.list_branches(
            params, sort=sort, search=search, is_active=is_active
        )

    async def list_all(self) -> Sequence[Branch]:
        return await self.branches.list_all()

    async def create(self, payload: BranchCreate) -> Branch:
        code = normalize_code(payload.code)
        if await self.branches.code_exists(code):
            raise ConflictError(
                "A branch with that code already exists.",
                code="branch_code_taken",
                details=[{"field": "code", "message": "Already in use."}],
            )

        branch = Branch(
            name=payload.name.strip(),
            code=code,
            address=payload.address,
            phone=payload.phone,
            is_active=payload.is_active,
        )
        await self.branches.add(branch)
        await self.session.commit()
        return branch

    async def update(self, branch_id: uuid.UUID, payload: BranchUpdate) -> Branch:
        branch = await self.get_or_404(branch_id)
        if payload.name is not None:
            branch.name = payload.name.strip()
        if "address" in payload.model_fields_set:
            branch.address = payload.address
        if "phone" in payload.model_fields_set:
            branch.phone = payload.phone
        if payload.is_active is not None:
            branch.is_active = payload.is_active
        await self.session.commit()
        return branch

    async def delete(self, branch_id: uuid.UUID) -> None:
        branch = await self.get_or_404(branch_id)
        assigned = await self.branches.count_users(branch.id)
        if assigned:
            raise ConflictError(
                f"{assigned} user(s) are still assigned to this branch.",
                code="branch_in_use",
            )
        branch.is_active = False
        branch.deleted_at = datetime.now(UTC)
        await self.session.commit()
