"""Staff account management. All business rules for users live here."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import ADMINISTRATOR_ROLE_NAME
from app.core.security import hash_password
from app.models.branch import Branch
from app.models.role import Role
from app.models.user import User
from app.repositories.branch import BranchRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserPasswordUpdate, UserUpdate
from app.utils.pagination import PageParams
from app.utils.text import normalize_email


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.branches = BranchRepository(session)
        self.tokens = RefreshTokenRepository(session)

    # --- Reads -------------------------------------------------------------
    async def get_or_404(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None or user.is_deleted:
            raise NotFoundError("User not found.", code="user_not_found")
        return user

    async def list_users(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        branch_id: uuid.UUID | None = None,
        role_id: uuid.UUID | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[User], int]:
        return await self.users.list_users(
            params,
            sort=sort,
            search=search,
            is_active=is_active,
            branch_id=branch_id,
            role_id=role_id,
        )

    # --- Writes ------------------------------------------------------------
    async def create(self, payload: UserCreate, *, actor: User) -> User:
        email = normalize_email(payload.email)
        if await self.users.email_exists(email):
            raise ConflictError(
                "A user with that email already exists.",
                code="email_already_used",
                details=[{"field": "email", "message": "Already in use."}],
            )
        if payload.is_superuser and not actor.is_superuser:
            raise ForbiddenError(
                "Only a superuser can grant superuser access.",
                code="superuser_required",
            )

        roles = await self._resolve_roles(payload.role_ids)
        self._assert_may_manage_administrator_role(actor, current=[], new=roles)
        branch = await self._resolve_branch(payload.branch_id)

        user = User(
            email=email,
            hashed_password=await anyio.to_thread.run_sync(hash_password, payload.password),
            full_name=payload.full_name.strip(),
            phone=payload.phone,
            is_active=payload.is_active,
            is_superuser=payload.is_superuser,
            branch=branch,
        )
        user.roles = list(roles)
        await self.users.add(user)
        await self.session.commit()
        return user

    async def update(self, user_id: uuid.UUID, payload: UserUpdate, *, actor: User) -> User:
        user = await self.get_or_404(user_id)
        provided = payload.model_fields_set

        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if "phone" in provided:
            user.phone = payload.phone

        if "branch_id" in provided:
            user.branch = await self._resolve_branch(payload.branch_id)

        if "role_ids" in provided and payload.role_ids is not None:
            new_roles = await self._resolve_roles(payload.role_ids)
            self._assert_may_manage_administrator_role(actor, current=user.roles, new=new_roles)
            user.roles = list(new_roles)

        if payload.is_active is not None and payload.is_active != user.is_active:
            if not payload.is_active:
                if user.id == actor.id:
                    raise BadRequestError(
                        "You cannot deactivate your own account.",
                        code="cannot_deactivate_self",
                    )
                await self._ensure_superuser_survives(user)
                await self.tokens.revoke_all_for_user(user.id)
            user.is_active = payload.is_active

        await self.session.commit()
        return user

    async def set_password(
        self,
        user_id: uuid.UUID,
        payload: UserPasswordUpdate,
        *,
        actor: User,
    ) -> None:
        user = await self.get_or_404(user_id)

        # An Administrator's password may only be changed by that same
        # Administrator through the current-password flow — never reset by
        # another administrator, a manager, or any other user.
        if user.is_administrator:
            audit(
                "password.reset_denied",
                actor_id=str(actor.id),
                target_id=str(user.id),
                reason="administrator_protected",
            )
            raise ForbiddenError(
                "An Administrator's password can only be changed by that Administrator, "
                "using their current password.",
                code="administrator_password_protected",
            )

        user.hashed_password = await anyio.to_thread.run_sync(hash_password, payload.password)
        # Force re-authentication everywhere after an administrative reset.
        await self.tokens.revoke_all_for_user(user.id)
        await self.session.commit()
        audit("password.reset_by_admin", actor_id=str(actor.id), target_id=str(user.id))

    async def deactivate(self, user_id: uuid.UUID, *, actor: User) -> None:
        user = await self.get_or_404(user_id)
        if user.id == actor.id:
            raise BadRequestError(
                "You cannot deactivate your own account.", code="cannot_deactivate_self"
            )
        await self._ensure_superuser_survives(user)

        user.is_active = False
        user.deleted_at = datetime.now(UTC)
        await self.tokens.revoke_all_for_user(user.id)
        await self.session.commit()

    # --- Internals ---------------------------------------------------------
    @staticmethod
    def _assert_may_manage_administrator_role(
        actor: User, *, current: Sequence[Role], new: Sequence[Role]
    ) -> None:
        """Only an Administrator may grant or revoke the Administrator role.

        Without this, anyone holding ``users:write`` (e.g. a Manager) could mint
        an administrator account with a known password and sign in as it —
        bypassing the protection of Administrator passwords entirely.
        """
        if actor.is_administrator:
            return
        if any(role.name == ADMINISTRATOR_ROLE_NAME for role in (*current, *new)):
            raise ForbiddenError(
                "Only an Administrator may assign or remove the Administrator role.",
                code="administrator_role_assignment_forbidden",
            )

    async def _ensure_superuser_survives(self, user: User) -> None:
        if not user.is_superuser:
            return
        remaining = await self.users.count_active_superusers(exclude_id=user.id)
        if remaining == 0:
            raise ConflictError("At least one active superuser must remain.", code="last_superuser")

    async def _resolve_roles(self, role_ids: Sequence[uuid.UUID]) -> Sequence[Role]:
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return []
        roles = await self.roles.get_many(unique_ids)
        if len(roles) != len(unique_ids):
            found = {role.id for role in roles}
            missing = [str(role_id) for role_id in unique_ids if role_id not in found]
            raise BadRequestError(
                "One or more roles do not exist.",
                code="invalid_roles",
                details=[{"field": "role_ids", "message": f"Unknown: {', '.join(missing)}"}],
            )
        return roles

    async def _resolve_branch(self, branch_id: uuid.UUID | None) -> Branch | None:
        if branch_id is None:
            return None
        branch = await self.branches.get(branch_id)
        if branch is None or branch.is_deleted:
            raise BadRequestError(
                "The selected branch does not exist.",
                code="invalid_branch",
                details=[{"field": "branch_id", "message": "Unknown branch."}],
            )
        return branch
