"""Staff account endpoints. Every route is permission-guarded."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.user import UserRepository
from app.schemas.common import Message, Page
from app.schemas.user import UserCreate, UserPasswordUpdate, UserRead, UserSummary, UserUpdate
from app.services.user import UserService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=Page[UserSummary],
    dependencies=[Depends(require_permissions(PermissionCode.USERS_READ))],
)
async def list_users(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120)] = None,
    is_active: Annotated[bool | None, Query()] = None,
    branch_id: Annotated[uuid.UUID | None, Query()] = None,
    role_id: Annotated[uuid.UUID | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. -created_at, email")] = None,
) -> Page[UserSummary]:
    users, total = await UserService(session).list_users(
        params,
        search=search,
        is_active=is_active,
        branch_id=branch_id,
        role_id=role_id,
        sort=parse_sort(sort, UserRepository.SORTABLE, default="-created_at"),
    )
    return Page.build(
        [UserSummary.model_validate(user) for user in users],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.USERS_WRITE))],
)
async def create_user(
    session: SessionDep,
    actor: CurrentUser,
    payload: UserCreate,
) -> UserRead:
    user = await UserService(session).create(payload, actor=actor)
    return UserRead.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permissions(PermissionCode.USERS_READ))],
)
async def get_user(session: SessionDep, user_id: uuid.UUID) -> UserRead:
    return UserRead.model_validate(await UserService(session).get_or_404(user_id))


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permissions(PermissionCode.USERS_WRITE))],
)
async def update_user(
    session: SessionDep,
    actor: CurrentUser,
    user_id: uuid.UUID,
    payload: UserUpdate,
) -> UserRead:
    user = await UserService(session).update(user_id, payload, actor=actor)
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/password",
    response_model=Message,
    summary="Reset another user's password",
    dependencies=[Depends(require_permissions(PermissionCode.USERS_RESET_PASSWORD))],
)
async def set_user_password(
    session: SessionDep,
    actor: CurrentUser,
    user_id: uuid.UUID,
    payload: UserPasswordUpdate,
) -> Message:
    await UserService(session).set_password(user_id, payload, actor=actor)
    return Message(message="Password has been reset.")


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.USERS_DELETE))],
)
async def deactivate_user(session: SessionDep, actor: CurrentUser, user_id: uuid.UUID) -> None:
    await UserService(session).deactivate(user_id, actor=actor)
