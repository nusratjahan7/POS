"""Authentication over HTTP: login, refresh rotation, logout, password change."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.core.config import settings
from app.models.user import User

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
CHANGE_PASSWORD = "/api/v1/auth/change-password"


async def test_login_returns_token_and_sets_refresh_cookie(
    client: AsyncClient, superuser: User
) -> None:
    response = await client.post(
        LOGIN, json={"email": superuser.email, "password": "SuperSecret1!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["email"] == superuser.email
    assert body["user"]["is_superuser"] is True
    assert body["user"]["permissions"] == ["*"]
    # The refresh token must never appear in the body.
    assert "refresh_token" not in body
    assert settings.REFRESH_COOKIE_NAME in response.cookies


async def test_login_is_case_insensitive_on_email(client: AsyncClient, superuser: User) -> None:
    response = await client.post(
        LOGIN, json={"email": superuser.email.upper(), "password": "SuperSecret1!"}
    )
    assert response.status_code == 200


async def test_login_with_wrong_password_is_unauthorized(
    client: AsyncClient, superuser: User
) -> None:
    response = await client.post(
        LOGIN, json={"email": superuser.email, "password": "WrongPassword1!"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_login_with_unknown_email_is_unauthorized(client: AsyncClient) -> None:
    response = await client.post(
        LOGIN, json={"email": "nobody@example.com", "password": "Whatever1!"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_inactive_user_cannot_log_in(
    client: AsyncClient, db_session: Any, superuser: User
) -> None:
    superuser.is_active = False
    await db_session.commit()

    response = await client.post(
        LOGIN, json={"email": superuser.email, "password": "SuperSecret1!"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_inactive"


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_me_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.get(ME, headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_me_returns_profile(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get(ME, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert body["roles"][0]["name"] == "Administrator"
    assert len(body["roles"][0]["permissions"]) > 0


async def test_refresh_rotates_the_token(client: AsyncClient, superuser: User) -> None:
    await client.post(LOGIN, json={"email": superuser.email, "password": "SuperSecret1!"})
    original = client.cookies[settings.REFRESH_COOKIE_NAME]

    response = await client.post(REFRESH)
    assert response.status_code == 200
    rotated = client.cookies[settings.REFRESH_COOKIE_NAME]
    assert rotated != original
    assert response.json()["access_token"]


async def test_replaying_a_rotated_refresh_token_is_rejected(
    client: AsyncClient, anon_client: AsyncClient, superuser: User
) -> None:
    await client.post(LOGIN, json={"email": superuser.email, "password": "SuperSecret1!"})
    original = client.cookies[settings.REFRESH_COOKIE_NAME]

    rotated_response = await client.post(REFRESH)
    assert rotated_response.status_code == 200
    rotated = client.cookies[settings.REFRESH_COOKIE_NAME]

    # Replay the original token from a cookie-less client.
    replay = await anon_client.post(REFRESH, json={"refresh_token": original})
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "refresh_token_revoked"

    # Replay detection invalidates the whole family, including the rotated token.
    following = await anon_client.post(REFRESH, json={"refresh_token": rotated})
    assert following.status_code == 401


async def test_refresh_without_token_is_unauthorized(anon_client: AsyncClient) -> None:
    response = await anon_client.post(REFRESH)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_refresh_token"


async def test_logout_revokes_the_refresh_token(
    client: AsyncClient, anon_client: AsyncClient, superuser: User
) -> None:
    await client.post(LOGIN, json={"email": superuser.email, "password": "SuperSecret1!"})
    token = client.cookies[settings.REFRESH_COOKIE_NAME]

    response = await client.post(LOGOUT)
    assert response.status_code == 200

    replay = await anon_client.post(REFRESH, json={"refresh_token": token})
    assert replay.status_code == 401


async def test_change_password_requires_the_current_password(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        CHANGE_PASSWORD,
        headers=auth_headers,
        json={"current_password": "NotThePassword1!", "new_password": "BrandNewPass1!"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_current_password"


async def test_change_password_revokes_existing_sessions(
    client: AsyncClient, anon_client: AsyncClient, auth_headers: dict[str, str], superuser: User
) -> None:
    await client.post(LOGIN, json={"email": superuser.email, "password": "SuperSecret1!"})
    refresh_token = client.cookies[settings.REFRESH_COOKIE_NAME]

    response = await client.post(
        CHANGE_PASSWORD,
        headers=auth_headers,
        json={"current_password": "SuperSecret1!", "new_password": "BrandNewPass1!"},
    )
    assert response.status_code == 200

    replay = await anon_client.post(REFRESH, json={"refresh_token": refresh_token})
    assert replay.status_code == 401


async def test_change_password_enforces_the_password_policy(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        CHANGE_PASSWORD,
        headers=auth_headers,
        json={"current_password": "SuperSecret1!", "new_password": "weak"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
