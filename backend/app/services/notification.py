"""In-app notifications: creation (fan-out) and the recipient's own reads.

Creation never commits — it runs inside the transaction of the action that caused
it (a sale, a stock movement, a settings change), so a notification lands exactly
when its cause lands. Read/mark operations own their transaction.

The outbound *email* transport lives separately in ``app.core.notifications``.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification import NotificationRepository
from app.utils.jsonable import jsonable
from app.utils.pagination import PageParams


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notifications = NotificationRepository(session)

    # --- Creation ----------------------------------------------------------
    async def push(
        self,
        *,
        type: str,
        severity: str,
        title: str,
        recipients: Sequence[uuid.UUID],
        body: str | None = None,
        entity_type: str | None = None,
        entity_id: str | uuid.UUID | None = None,
        data: dict[str, Any] | None = None,
    ) -> list[Notification]:
        """Fan a notification out to each recipient. Does not commit."""
        unique = list(dict.fromkeys(recipients))
        if not unique:
            return []
        rows = [
            Notification(
                user_id=user_id,
                type=type,
                severity=severity,
                title=title,
                body=body,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                data=jsonable(data) if data is not None else None,
            )
            for user_id in unique
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def push_to_permission(
        self,
        code: str,
        *,
        exclude_user_id: uuid.UUID | None = None,
        **payload: Any,
    ) -> list[Notification]:
        """Notify every user who holds *code*, minus the actor. Does not commit."""
        recipients = await self.notifications.recipients_with_permission(
            code, exclude_user_id=exclude_user_id
        )
        return await self.push(recipients=recipients, **payload)

    # --- Recipient reads ---------------------------------------------------
    async def list_for_user(
        self,
        user: User,
        params: PageParams,
        *,
        unread: bool | None = None,
        type: str | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Notification], int]:
        return await self.notifications.list_for_user(
            user.id, params, unread=unread, type=type, sort=sort
        )

    async def unread_count(self, user: User) -> int:
        return await self.notifications.unread_count(user.id)

    async def mark_read(self, user: User, notification_id: uuid.UUID) -> Notification:
        row = await self.notifications.get_for_user(user.id, notification_id)
        if row is None:
            raise NotFoundError("Notification not found.", code="notification_not_found")
        if row.read_at is None:
            row.read_at = datetime.now(UTC)
            await self.session.commit()
        return row

    async def mark_all_read(self, user: User) -> None:
        await self.notifications.mark_all_read(user.id)
        await self.session.commit()
