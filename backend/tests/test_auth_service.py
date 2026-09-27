"""Service-level authentication rules (bypassing HTTP)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, InvalidCredentialsError, UnauthorizedError
from app.models.user import User
from app.services.auth import AuthService


async def test_authenticate_issues_access_and_refresh_tokens(
    db_session: AsyncSession, superuser: User
) -> None:
    issued = await AuthService(db_session).authenticate(
        email=superuser.email, password="SuperSecret1!"
    )
    assert issued.access_token
    assert issued.refresh_token
    assert issued.user.id == superuser.id


async def test_authenticate_updates_last_login(db_session: AsyncSession, superuser: User) -> None:
    assert superuser.last_login_at is None
    await AuthService(db_session).authenticate(email=superuser.email, password="SuperSecret1!")
    assert superuser.last_login_at is not None


async def test_authenticate_rejects_bad_password(db_session: AsyncSession, superuser: User) -> None:
    with pytest.raises(InvalidCredentialsError):
        await AuthService(db_session).authenticate(
            email=superuser.email, password="WrongPassword1!"
        )


async def test_refresh_rotates_and_replay_revokes_the_family(
    db_session: AsyncSession, superuser: User
) -> None:
    service = AuthService(db_session)
    first = await service.authenticate(email=superuser.email, password="SuperSecret1!")

    second = await service.refresh(first.refresh_token)
    assert second.refresh_token != first.refresh_token

    # Replaying the consumed token is treated as compromise.
    with pytest.raises(UnauthorizedError):
        await service.refresh(first.refresh_token)

    # ...and the descendant token is revoked too.
    with pytest.raises(UnauthorizedError):
        await service.refresh(second.refresh_token)


async def test_logout_is_idempotent(db_session: AsyncSession, superuser: User) -> None:
    service = AuthService(db_session)
    issued = await service.authenticate(email=superuser.email, password="SuperSecret1!")

    await service.logout(issued.refresh_token)
    # Second call must not raise.
    await service.logout(issued.refresh_token)

    with pytest.raises(UnauthorizedError):
        await service.refresh(issued.refresh_token)


async def test_logout_without_token_is_a_noop(db_session: AsyncSession) -> None:
    await AuthService(db_session).logout(None)


async def test_change_password_rejects_reusing_the_same_password(
    db_session: AsyncSession, superuser: User
) -> None:
    service = AuthService(db_session)
    with pytest.raises(BadRequestError) as excinfo:
        await service.change_password(
            superuser,
            current_password="SuperSecret1!",
            new_password="SuperSecret1!",
        )
    assert excinfo.value.code == "password_unchanged"


async def test_change_password_then_login_with_new_password(
    db_session: AsyncSession, superuser: User
) -> None:
    service = AuthService(db_session)
    await service.change_password(
        superuser, current_password="SuperSecret1!", new_password="BrandNewPass1!"
    )

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email=superuser.email, password="SuperSecret1!")

    issued = await service.authenticate(email=superuser.email, password="BrandNewPass1!")
    assert issued.access_token
