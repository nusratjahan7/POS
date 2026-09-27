"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status

from app.api.cookies import clear_refresh_cookie, set_refresh_cookie
from app.api.deps import CurrentUser, SessionDep, client_ip, rate_limit
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.common import Message
from app.schemas.user import UserRead
from app.services.auth import AuthService, IssuedSession

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(response: Response, issued: IssuedSession) -> TokenResponse:
    set_refresh_cookie(response, issued.refresh_token)
    return TokenResponse(
        access_token=issued.access_token,
        expires_in=issued.expires_in,
        user=UserRead.model_validate(issued.user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for an access token",
    dependencies=[Depends(rate_limit("login", settings.LOGIN_RATE_LIMIT))],
)
async def login(
    request: Request,
    response: Response,
    session: SessionDep,
    payload: LoginRequest,
) -> TokenResponse:
    issued = await AuthService(session).authenticate(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )
    return _token_response(response, issued)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate the refresh token and issue a new access token",
    dependencies=[Depends(rate_limit("refresh", "60/minute"))],
)
async def refresh(
    request: Request,
    response: Response,
    session: SessionDep,
    payload: Annotated[RefreshRequest | None, Body()] = None,
) -> TokenResponse:
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME) or (
        payload.refresh_token if payload else None
    )
    if not token:
        raise UnauthorizedError("No refresh token was provided.", code="missing_refresh_token")

    issued = await AuthService(session).refresh(
        token,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )
    return _token_response(response, issued)


@router.post("/logout", response_model=Message, summary="Revoke the current refresh token")
async def logout(request: Request, response: Response, session: SessionDep) -> Message:
    await AuthService(session).logout(request.cookies.get(settings.REFRESH_COOKIE_NAME))
    clear_refresh_cookie(response)
    return Message(message="Signed out.")


@router.get("/me", response_model=UserRead, summary="The authenticated user")
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.post(
    "/change-password",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Change your own password",
    dependencies=[Depends(rate_limit("change-password", "10/hour"))],
)
async def change_password(
    response: Response,
    session: SessionDep,
    user: CurrentUser,
    payload: ChangePasswordRequest,
) -> Message:
    await AuthService(session).change_password(
        user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    # All sessions were revoked; drop the cookie so the client re-authenticates.
    clear_refresh_cookie(response)
    return Message(message="Password updated. Please sign in again.")
