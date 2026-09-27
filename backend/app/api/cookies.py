"""Refresh-token cookie helpers.

The refresh token is a httpOnly cookie scoped to the auth endpoints, so it is
never exposed to JavaScript and is not attached to ordinary API calls.
"""

from __future__ import annotations

from fastapi import Response

from app.core.config import settings


def refresh_cookie_path() -> str:
    return f"{settings.API_V1_PREFIX}/auth"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_ttl_seconds,
        path=refresh_cookie_path(),
        domain=settings.COOKIE_DOMAIN or None,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=refresh_cookie_path(),
        domain=settings.COOKIE_DOMAIN or None,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )
