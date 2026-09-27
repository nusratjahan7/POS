"""Access-token expiry, token-type confusion, and endpoint protection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from httpx import AsyncClient

from app.core.config import settings
from app.models.user import User

ME = "/api/v1/auth/me"
REFRESH = "/api/v1/auth/refresh"
USERS = "/api/v1/users"


def _craft(subject: str, token_type: str, *, expires_in: timedelta) -> str:
    """Build a token directly, so expiry can be tested without waiting."""
    now = datetime.now(UTC)
    claims = {
        "sub": subject,
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": int((now - timedelta(minutes=1)).timestamp()),
        "exp": int((now + expires_in).timestamp()),
    }
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def test_expired_access_token_reports_token_expired(
    client: AsyncClient, superuser: User
) -> None:
    expired = _craft(str(superuser.id), "access", expires_in=timedelta(minutes=-5))

    response = await client.get(ME, headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


async def test_access_token_is_not_accepted_as_a_refresh_token(
    client: AsyncClient, superuser: User
) -> None:
    access = _craft(str(superuser.id), "access", expires_in=timedelta(minutes=5))

    response = await client.post(REFRESH, json={"refresh_token": access})

    assert response.status_code == 401


async def test_token_for_an_unknown_subject_is_rejected(client: AsyncClient) -> None:
    orphan = _craft(str(uuid.uuid4()), "access", expires_in=timedelta(minutes=5))

    response = await client.get(ME, headers={"Authorization": f"Bearer {orphan}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "account_unavailable"


async def test_protected_endpoints_reject_anonymous_callers(client: AsyncClient) -> None:
    assert (await client.get(ME)).status_code == 401
    assert (await client.get(USERS)).status_code == 401


async def test_protected_endpoint_accepts_a_valid_token(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(USERS, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["total"] >= 1
