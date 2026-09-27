"""Authentication use-cases: login, refresh rotation, logout, password change.

Password verification and hashing are CPU-bound, so they are offloaded to a
worker thread — never run Argon2 on the event loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    InvalidCredentialsError,
    UnauthorizedError,
)
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_and_update_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """A real hash used to equalise timing when the account does not exist."""
    return hash_password("timing-equalisation-placeholder")


@dataclass(frozen=True, slots=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = RefreshTokenRepository(session)

    # --- Authentication ----------------------------------------------------
    async def authenticate(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> IssuedSession:
        user = await self.users.get_by_email(email)
        if user is None:
            await anyio.to_thread.run_sync(verify_password, password, _dummy_hash())
            raise InvalidCredentialsError()

        valid, new_hash = await anyio.to_thread.run_sync(
            verify_and_update_password, password, user.hashed_password
        )
        if not valid:
            raise InvalidCredentialsError()
        if new_hash is not None:
            user.hashed_password = new_hash

        if not user.is_active:
            raise ForbiddenError("This account has been deactivated.", code="account_inactive")

        user.last_login_at = datetime.now(UTC)
        issued, _ = await self._issue(user, user_agent=user_agent, ip_address=ip_address)
        await self.session.commit()
        return issued

    async def refresh(
        self,
        refresh_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> IssuedSession:
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
        record = await self.tokens.get_by_hash(hash_token(refresh_token))
        if record is None or str(record.user_id) != payload.sub:
            raise UnauthorizedError("Invalid refresh token.", code="invalid_refresh_token")

        if record.is_revoked:
            # A rotated token was replayed — treat the whole family as compromised.
            await self.tokens.revoke_all_for_user(record.user_id)
            await self.session.commit()
            raise UnauthorizedError("Refresh token has been revoked.", code="refresh_token_revoked")
        if record.is_expired:
            raise UnauthorizedError("Refresh token has expired.", code="refresh_token_expired")

        user = await self.users.get_usable(record.user_id)
        if user is None:
            raise ForbiddenError("This account is no longer active.", code="account_inactive")

        issued, new_record = await self._issue(user, user_agent=user_agent, ip_address=ip_address)
        record.revoked_at = datetime.now(UTC)
        record.replaced_by_id = new_record.id
        await self.session.commit()
        return issued

    async def logout(self, refresh_token: str | None) -> None:
        """Idempotent: revokes the presented token if it is still active."""
        if not refresh_token:
            return
        record = await self.tokens.get_by_hash(hash_token(refresh_token))
        if record is not None and not record.is_revoked:
            record.revoked_at = datetime.now(UTC)
            await self.session.commit()

    async def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
    ) -> None:
        if not await anyio.to_thread.run_sync(
            verify_password, current_password, user.hashed_password
        ):
            raise BadRequestError("Current password is incorrect.", code="invalid_current_password")
        if await anyio.to_thread.run_sync(verify_password, new_password, user.hashed_password):
            raise BadRequestError(
                "The new password must differ from the current one.",
                code="password_unchanged",
            )

        user.hashed_password = await anyio.to_thread.run_sync(hash_password, new_password)
        # Every other session is invalidated as a security precaution.
        await self.tokens.revoke_all_for_user(user.id)
        await self.session.commit()

    # --- Internals ---------------------------------------------------------
    async def _issue(
        self,
        user: User,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[IssuedSession, RefreshToken]:
        access = create_access_token(str(user.id))
        refresh = create_refresh_token(str(user.id))
        record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh.token),
            jti=refresh.jti,
            expires_at=refresh.expires_at,
            user_agent=user_agent[:255] if user_agent else None,
            ip_address=ip_address[:45] if ip_address else None,
        )
        await self.tokens.add(record)
        issued = IssuedSession(
            access_token=access.token,
            refresh_token=refresh.token,
            expires_in=settings.access_token_ttl_seconds,
            user=user,
        )
        return issued, record
