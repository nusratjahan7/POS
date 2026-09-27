"""Administrator password protection.

An Administrator's password may only be changed by that same Administrator, with
their current password. Every other path — another administrator, a manager, the
admin reset endpoint, or the emailed token link — is refused.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import select

from app.core.logging import redact
from app.core.security import hash_token
from app.models.password_reset import PasswordResetToken
from app.models.user import User

USERS = "/api/v1/users"
CHANGE_PASSWORD = "/api/v1/auth/change-password"
FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"


def _new_user(seeded: SimpleNamespace, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": "new.hire@example.com",
        "full_name": "New Hire",
        "password": "Str0ngPass!",
        "role_ids": [str(seeded.roles["Cashier"].id)],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Admin reset endpoint may never target an Administrator
# ---------------------------------------------------------------------------
async def test_an_administrator_cannot_reset_another_administrator(
    client: AsyncClient, auth_headers: dict[str, str], administrator: User
) -> None:
    response = await client.post(
        f"{USERS}/{administrator.id}/password",
        headers=auth_headers,
        json={"password": "Hijack123!"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "administrator_password_protected"


async def test_an_administrator_cannot_reset_their_own_password_here(
    client: AsyncClient, auth_headers: dict[str, str], superuser: User
) -> None:
    """Even for yourself, this endpoint is refused — use change-password instead."""
    response = await client.post(
        f"{USERS}/{superuser.id}/password",
        headers=auth_headers,
        json={"password": "Hijack123!"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "administrator_password_protected"


async def test_non_administrators_cannot_reset_an_administrator(
    client: AsyncClient,
    manager_headers: dict[str, str],
    inventory_manager_headers: dict[str, str],
    cashier_headers: dict[str, str],
    administrator: User,
) -> None:
    for headers in (manager_headers, inventory_manager_headers, cashier_headers):
        response = await client.post(
            f"{USERS}/{administrator.id}/password",
            headers=headers,
            json={"password": "Hijack123!"},
        )
        assert response.status_code == 403, headers
        assert response.json()["error"]["code"] == "insufficient_permissions"


async def test_a_denied_reset_leaves_the_password_unchanged(
    client: AsyncClient,
    auth_headers: dict[str, str],
    administrator: User,
    login_as: Any,
) -> None:
    await client.post(
        f"{USERS}/{administrator.id}/password",
        headers=auth_headers,
        json={"password": "Hijack123!"},
    )

    # The original password still works, and the attempted one does not.
    assert await login_as(administrator.email, "ManagerPass1!")

    refused = await client.post(
        "/api/v1/auth/login",
        json={"email": administrator.email, "password": "Hijack123!"},
    )
    assert refused.status_code == 401


async def test_an_administrator_can_still_reset_a_non_administrator(
    client: AsyncClient, auth_headers: dict[str, str], cashier: User
) -> None:
    response = await client.post(
        f"{USERS}/{cashier.id}/password",
        headers=auth_headers,
        json={"password": "ResetPass1!"},
    )

    assert response.status_code == 200
    login = await client.post(
        "/api/v1/auth/login", json={"email": cashier.email, "password": "ResetPass1!"}
    )
    assert login.status_code == 200


# ---------------------------------------------------------------------------
# Self-service change is the one sanctioned path
# ---------------------------------------------------------------------------
async def test_an_administrator_changes_their_own_password_with_the_current_one(
    client: AsyncClient, administrator: User, login_as: Any
) -> None:
    headers = await login_as(administrator.email, "ManagerPass1!")

    response = await client.post(
        CHANGE_PASSWORD,
        headers=headers,
        json={"current_password": "ManagerPass1!", "new_password": "RotatedPass1!"},
    )

    assert response.status_code == 200, response.text
    assert (
        await client.post(
            "/api/v1/auth/login",
            json={"email": administrator.email, "password": "RotatedPass1!"},
        )
    ).status_code == 200


async def test_a_wrong_current_password_is_rejected(
    client: AsyncClient, administrator: User, login_as: Any
) -> None:
    headers = await login_as(administrator.email, "ManagerPass1!")

    response = await client.post(
        CHANGE_PASSWORD,
        headers=headers,
        json={"current_password": "WrongPass1!", "new_password": "RotatedPass1!"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_current_password"


# ---------------------------------------------------------------------------
# The emailed token flow is closed to administrators
# ---------------------------------------------------------------------------
async def test_forgot_password_mints_no_token_for_an_administrator(
    client: AsyncClient, administrator: User, db_session: Any, login_as: Any
) -> None:
    response = await client.post(FORGOT, json={"email": administrator.email})

    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]

    # No reset token was issued, and the password is untouched.
    tokens = await db_session.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == administrator.id)
    )
    assert tokens.scalars().all() == []
    assert await login_as(administrator.email, "ManagerPass1!")


async def test_a_reset_token_cannot_change_an_administrator_password(
    client: AsyncClient, administrator: User, db_session: Any, login_as: Any
) -> None:
    raw = "forced-token-for-the-admin-account"
    db_session.add(
        PasswordResetToken(
            user_id=administrator.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
    )
    await db_session.commit()

    response = await client.post(RESET, json={"token": raw, "new_password": "RotatedPass1!"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "administrator_password_protected"
    assert await login_as(administrator.email, "ManagerPass1!")


# ---------------------------------------------------------------------------
# Only an Administrator may hand out the Administrator role
# ---------------------------------------------------------------------------
async def test_a_manager_cannot_assign_the_administrator_role(
    client: AsyncClient, manager_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.post(
        USERS,
        headers=manager_headers,
        json=_new_user(seeded, role_ids=[str(seeded.roles["Administrator"].id)]),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "administrator_role_assignment_forbidden"


async def test_an_administrator_can_assign_the_administrator_role(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.post(
        USERS,
        headers=auth_headers,
        json=_new_user(seeded, role_ids=[str(seeded.roles["Administrator"].id)]),
    )

    assert response.status_code == 201, response.text


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
async def test_a_password_change_is_audited_without_the_password(
    client: AsyncClient, administrator: User, login_as: Any
) -> None:
    headers = await login_as(administrator.email, "ManagerPass1!")
    new_password = "RotatedPass1!"

    with patch("app.services.auth.audit") as audited:
        response = await client.post(
            CHANGE_PASSWORD,
            headers=headers,
            json={"current_password": "ManagerPass1!", "new_password": new_password},
        )

    assert response.status_code == 200, response.text
    events = [call.args[0] for call in audited.call_args_list]
    assert "password.changed" in events
    # No audit call ever carries the password.
    assert new_password not in str(audited.call_args_list)
    assert "ManagerPass1!" not in str(audited.call_args_list)


def test_the_audit_helper_redacts_secret_fields() -> None:
    """Belt-and-braces: even if a caller passes a secret, it is masked."""
    assert redact({"user_id": "u1", "password": "secret"}) == {
        "user_id": "u1",
        "password": "***redacted***",
    }
