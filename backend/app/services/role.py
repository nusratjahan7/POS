"""Role and permission use-cases."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.models.permission import Permission
from app.models.role import Role
from app.repositories.permission import PermissionRepository
from app.repositories.role import RoleRepository
from app.schemas.role import RoleCreate, RoleUpdate
from app.utils.pagination import PageParams


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.roles = RoleRepository(session)
        self.permissions = PermissionRepository(session)

    # --- Reads -------------------------------------------------------------
    async def get_or_404(self, role_id: uuid.UUID) -> Role:
        role = await self.roles.get(role_id)
        if role is None or role.is_deleted:
            raise NotFoundError("Role not found.", code="role_not_found")
        return role

    async def list_roles(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Role], int]:
        return await self.roles.list_roles(params, sort=sort, search=search)

    async def list_all(self) -> Sequence[Role]:
        return await self.roles.list_all()

    async def list_permissions(self) -> Sequence[Permission]:
        return await self.permissions.list_all()

    # --- Writes ------------------------------------------------------------
    async def create(self, payload: RoleCreate) -> Role:
        name = payload.name.strip()
        if await self.roles.name_exists(name):
            raise ConflictError(
                "A role with that name already exists.",
                code="role_name_taken",
                details=[{"field": "name", "message": "Already in use."}],
            )

        role = Role(
            name=name,
            description=payload.description,
            is_system=False,
        )
        role.permissions = list(await self._resolve_permissions(payload.permission_codes))
        await self.roles.add(role)
        await self.session.commit()
        return role

    async def update(self, role_id: uuid.UUID, payload: RoleUpdate) -> Role:
        role = await self.get_or_404(role_id)

        if payload.name is not None:
            name = payload.name.strip()
            if role.is_system and name != role.name:
                raise ForbiddenError(
                    "System roles cannot be renamed.", code="system_role_immutable"
                )
            if await self.roles.name_exists(name, exclude_id=role.id):
                raise ConflictError(
                    "A role with that name already exists.",
                    code="role_name_taken",
                    details=[{"field": "name", "message": "Already in use."}],
                )
            role.name = name

        if "description" in payload.model_fields_set:
            role.description = payload.description

        if payload.permission_codes is not None:
            role.permissions = list(await self._resolve_permissions(payload.permission_codes))

        await self.session.commit()
        return role

    async def delete(self, role_id: uuid.UUID) -> None:
        role = await self.get_or_404(role_id)
        if role.is_system:
            raise ForbiddenError("System roles cannot be deleted.", code="system_role_immutable")

        assigned = await self.roles.count_users(role.id)
        if assigned:
            raise ConflictError(f"This role is assigned to {assigned} user(s).", code="role_in_use")

        role.deleted_at = datetime.now(UTC)
        await self.session.commit()

    # --- Internals ---------------------------------------------------------
    async def _resolve_permissions(self, codes: Sequence[str]) -> Sequence[Permission]:
        unique = list(dict.fromkeys(codes))
        if not unique:
            return []
        permissions = await self.permissions.get_by_codes(unique)
        if len(permissions) != len(unique):
            found = {permission.code for permission in permissions}
            missing = [code for code in unique if code not in found]
            raise BadRequestError(
                "One or more permissions are unknown.",
                code="invalid_permissions",
                details=[
                    {"field": "permission_codes", "message": f"Unknown: {', '.join(missing)}"}
                ],
            )
        return permissions
