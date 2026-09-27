from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, or_, select

from app.models.role import Role
from app.models.user import User
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern, normalize_email


class UserRepository(BaseRepository[User]):
    model = User

    SORTABLE: ClassVar[dict[str, Any]] = {
        "created_at": User.created_at,
        "updated_at": User.updated_at,
        "email": User.email,
        "full_name": User.full_name,
        "last_login_at": User.last_login_at,
    }

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(User.email == normalize_email(email))
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalars().unique().one_or_none()

    async def get_usable(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user that is neither soft-deleted nor deactivated."""
        stmt = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        return (await self.session.execute(stmt)).scalars().unique().one_or_none()

    async def email_exists(self, email: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(User.id).where(User.email == normalize_email(email))
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    async def count_active_superusers(self, *, exclude_id: uuid.UUID | None = None) -> int:
        """Used to guarantee the system always retains one usable superuser."""
        stmt = select(func.count(User.id)).where(
            User.is_superuser.is_(True),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return int((await self.session.execute(stmt)).scalar_one())

    def build_list_query(
        self,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        branch_id: uuid.UUID | None = None,
        role_id: uuid.UUID | None = None,
        include_deleted: bool = False,
    ) -> Select[Any]:
        stmt = select(User)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    User.email.ilike(pattern, escape="\\"),
                    User.full_name.ilike(pattern, escape="\\"),
                )
            )
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        if branch_id is not None:
            stmt = stmt.where(User.branch_id == branch_id)
        if role_id is not None:
            stmt = stmt.where(User.roles.any(Role.id == role_id))
        return stmt

    async def list_users(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[User], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(User.created_at.desc())
        return await self.paginate(stmt, params)
