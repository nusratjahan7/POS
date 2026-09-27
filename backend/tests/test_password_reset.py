"""Password reset: requesting, consuming, and the single-use guarantees.

These exercise the **non-administrator** path. Administrator accounts are
deliberately excluded from the emailed reset flow (see
``test_admin_password_protection.py``), so the subject here is a Cashier.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_token
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.auth import AuthService

FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"

# The `cashier` fixture's password — a non-administrator, resettable account.
CURRENT_PASSWORD = "CashierPass1!"
NEW_PASSWORD = "RotatedPass1!"


async def _issue(db_session: AsyncSession, email: str) -> str:
    """Mint a reset token the way the endpoint does, returning the raw value."""
    issued = await AuthService(db_session).request_password_reset(email=email)
    assert issued is not None
    return issued.token


async def _token_count(db_session: AsyncSession, user_id: object) -> int:
    stmt = select(func.count(PasswordResetToken.id)).where(PasswordResetToken.user_id == user_id)
    return int((await db_session.execute(stmt)).scalar_one())


async def test_forgot_password_responds_identically_for_known_and_unknown_email(
    client: AsyncClient, cashier: User
) -> None:
    """No account enumeration: the response must not reveal registration."""

    known = await client.post(FORGOT, json={"email": cashier.email})
    unknown = await client.post(FORGOT, json={"email": "nobody@example.com"})

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()


async def test_forgot_password_never_puts_the_token_in_the_response(
    client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    issued = await AuthService(db_session).request_password_reset(email=cashier.email)
    assert issued is not None

    response = await client.post(FORGOT, json={"email": cashier.email})

    assert response.status_code == 200
    assert issued.token not in response.text
    assert set(response.json()) == {"message"}


async def test_only_the_digest_is_persisted(db_session: AsyncSession, cashier: User) -> None:
    token = await _issue(db_session, cashier.email)

    record = (await db_session.execute(select(PasswordResetToken))).scalars().one()

    assert record.token_hash == hash_token(token)
    assert record.token_hash != token
    assert record.is_usable


async def test_requesting_a_new_link_supersedes_the_previous_one(
    client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    stale = await _issue(db_session, cashier.email)
    fresh = await _issue(db_session, cashier.email)
    assert stale != fresh

    rejected = await client.post(RESET, json={"token": stale, "new_password": NEW_PASSWORD})
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "reset_token_used"

    accepted = await client.post(RESET, json={"token": fresh, "new_password": NEW_PASSWORD})
    assert accepted.status_code == 200


async def test_reset_then_login_with_the_new_password(
    client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    token = await _issue(db_session, cashier.email)

    response = await client.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 200

    old = await client.post(LOGIN, json={"email": cashier.email, "password": CURRENT_PASSWORD})
    assert old.status_code == 401

    new = await client.post(LOGIN, json={"email": cashier.email, "password": NEW_PASSWORD})
    assert new.status_code == 200


async def test_reset_token_is_single_use(
    client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    token = await _issue(db_session, cashier.email)

    first = await client.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})
    assert first.status_code == 200

    second = await client.post(RESET, json={"token": token, "new_password": "AnotherPass1!"})
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "reset_token_used"


async def test_expired_reset_token_is_rejected(
    client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    token = await _issue(db_session, cashier.email)
    record = (await db_session.execute(select(PasswordResetToken))).scalars().one()
    record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    response = await client.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "reset_token_expired"


async def test_unknown_reset_token_is_rejected(client: AsyncClient) -> None:
    response = await client.post(RESET, json={"token": "x" * 43, "new_password": NEW_PASSWORD})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_reset_token"


async def test_reset_password_revokes_every_existing_session(
    client: AsyncClient, anon_client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    await client.post(LOGIN, json={"email": cashier.email, "password": CURRENT_PASSWORD})
    hijacked = client.cookies[settings.REFRESH_COOKIE_NAME]

    token = await _issue(db_session, cashier.email)
    response = await client.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 200

    replay = await anon_client.post(REFRESH, json={"refresh_token": hijacked})
    assert replay.status_code == 401


async def test_reset_password_enforces_the_password_policy(
    client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    token = await _issue(db_session, cashier.email)

    response = await client.post(RESET, json={"token": token, "new_password": "weak"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_reset_password_rejects_reusing_the_current_password(
    client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    token = await _issue(db_session, cashier.email)

    response = await client.post(RESET, json={"token": token, "new_password": CURRENT_PASSWORD})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "password_unchanged"


async def test_deactivated_account_cannot_request_a_reset(
    client: AsyncClient, db_session: AsyncSession, cashier: User
) -> None:
    cashier.is_active = False
    await db_session.commit()

    response = await client.post(FORGOT, json={"email": cashier.email})

    assert response.status_code == 200  # still deliberately generic
    assert await _token_count(db_session, cashier.id) == 0


async def test_service_returns_none_for_an_unknown_account(db_session: AsyncSession) -> None:
    issued = await AuthService(db_session).request_password_reset(email="ghost@example.com")
    assert issued is None
