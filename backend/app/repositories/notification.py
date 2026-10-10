from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, or_, select, update

from app.models.associations import role_permissions, user_roles
from app.models.notification import Notification
from app.models.permission import Permission
from app.models.user import User
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    SORTABLE: ClassVar[dict[str, Any]] = {
        "created_at": Notification.created_at,
    }

    # --- Recipient reads ---------------------------------------------------
    async def list_for_user(
        self,
        user_id: uuid.UUID,
        params: PageParams,
        *,
        unread: bool | None = None,
        type: str | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Notification], int]:
        stmt: Select[Any] = select(Notification).where(Notification.user_id == user_id)
        if unread is True:
            stmt = stmt.where(Notification.read_at.is_(None))
        elif unread is False:
            stmt = stmt.where(Notification.read_at.is_not(None))
        if type:
            stmt = stmt.where(Notification.type == type)

        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Notification.created_at.desc())
        return await self.paginate(stmt, params)

    async def unread_count(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_for_user(
        self, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=func.now())
        )
        await self.session.execute(stmt)

    # --- Recipient resolution ---------------------------------------------
    async def recipients_with_permission(
        self, code: str, *, exclude_user_id: uuid.UUID | None = None
    ) -> Sequence[uuid.UUID]:
        """Active users who hold *code* — or are superusers (they bypass checks).

        Users with no roles at all are still included when they are superusers,
        hence the outer joins.
        """
        stmt = (
            select(User.id)
            .outerjoin(user_roles, user_roles.c.user_id == User.id)
            .outerjoin(role_permissions, role_permissions.c.role_id == user_roles.c.role_id)
            .outerjoin(Permission, Permission.id == role_permissions.c.permission_id)
            .where(
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                or_(User.is_superuser.is_(True), Permission.code == code),
            )
            .distinct()
        )
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return list((await self.session.execute(stmt)).scalars().all())
