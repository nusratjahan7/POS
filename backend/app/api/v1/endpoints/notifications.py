"""Notification centre endpoints.

Everything here is scoped to the authenticated user: you can only ever read or
mark *your own* notifications. Rows are created by the domain services, not by
this module.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.notification import NotificationRepository
from app.schemas.common import Page
from app.schemas.notification import NotificationRead, NotificationType, NotificationUnread
from app.services.notification import NotificationService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/notifications", tags=["notifications"])

_read_guard = Depends(require_permissions(PermissionCode.NOTIFICATIONS_READ))


@router.get(
    "",
    response_model=Page[NotificationRead],
    dependencies=[_read_guard],
    summary="Your notifications, newest first",
)
async def list_notifications(
    session: SessionDep,
    actor: CurrentUser,
    params: Pagination,
    unread: Annotated[bool | None, Query(description="Only unread when true")] = None,
    type: Annotated[NotificationType | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. -created_at")] = None,
) -> Page[NotificationRead]:
    rows, total = await NotificationService(session).list_for_user(
        actor,
        params,
        unread=unread,
        type=type,
        sort=parse_sort(sort, NotificationRepository.SORTABLE, default="-created_at"),
    )
    return Page.build(
        [NotificationRead.model_validate(row) for row in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnread,
    dependencies=[_read_guard],
    summary="Your unread notification count",
)
async def unread_count(session: SessionDep, actor: CurrentUser) -> NotificationUnread:
    return NotificationUnread(unread=await NotificationService(session).unread_count(actor))


@router.post(
    "/read-all",
    response_model=NotificationUnread,
    dependencies=[_read_guard],
    summary="Mark every notification as read",
)
async def mark_all_read(session: SessionDep, actor: CurrentUser) -> NotificationUnread:
    await NotificationService(session).mark_all_read(actor)
    return NotificationUnread(unread=0)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    dependencies=[_read_guard],
    summary="Mark one notification as read",
)
async def mark_read(
    session: SessionDep, actor: CurrentUser, notification_id: uuid.UUID
) -> NotificationRead:
    row = await NotificationService(session).mark_read(actor, notification_id)
    return NotificationRead.model_validate(row)
