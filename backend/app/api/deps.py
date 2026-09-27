"""Reusable ``Annotated`` dependencies shared by every endpoint."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, RateLimitError, TokenError, UnauthorizedError
from app.core.rate_limit import parse_limit, rate_limiter
from app.core.security import TokenType, decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.utils.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageParams

# --- Database --------------------------------------------------------------
SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Pagination ------------------------------------------------------------
def pagination(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Rows per page"),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


Pagination = Annotated[PageParams, Depends(pagination)]

# --- Authentication --------------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication credentials were not provided.")

    payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError as exc:
        raise TokenError("The token subject is invalid.") from exc

    user = await UserRepository(session).get_usable(user_id)
    if user is None:
        raise UnauthorizedError("This account is not available.", code="account_unavailable")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# --- Authorization ---------------------------------------------------------
def require_permissions(*codes: str) -> Callable[..., Awaitable[User]]:
    """Build a dependency enforcing *all* supplied permission codes.

    Use in the decorator: ``dependencies=[Depends(require_permissions(...))]``.
    Superusers pass automatically (see ``User.has_permission``).
    """

    async def dependency(user: CurrentUser) -> User:
        missing = [code for code in codes if not user.has_permission(code)]
        if missing:
            raise ForbiddenError(
                "You do not have the required permission(s).",
                code="insufficient_permissions",
                details=[{"field": "permissions", "message": f"Missing: {', '.join(missing)}"}],
            )
        return user

    return dependency


async def require_superuser(user: CurrentUser) -> User:
    if not user.is_superuser:
        raise ForbiddenError("Superuser access is required.", code="superuser_required")
    return user


# --- Rate limiting ---------------------------------------------------------
def client_ip(request: Request) -> str | None:
    """Best-effort client IP.

    ``X-Forwarded-For`` is only trustworthy behind a proxy that overwrites it;
    it is used here as a convenience and must not be treated as an auth signal.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def rate_limit(scope: str, limit: str) -> Callable[..., Awaitable[None]]:
    """Build a dependency that rate-limits by client IP within ``scope``."""

    async def dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        count, window = parse_limit(limit)
        key = f"{scope}:{client_ip(request) or 'unknown'}"
        retry_after = rate_limiter.check(key, count, window)
        if retry_after is not None:
            raise RateLimitError(retry_after=retry_after)

    return dependency
