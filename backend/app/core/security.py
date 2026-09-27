"""Password hashing and JWT issuing/verification.

Access tokens are short-lived and carry only the subject + a JWT id. Refresh
tokens are opaque to clients in the sense that only a SHA-256 hash of the token
is persisted, so a database leak cannot be replayed against the API.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.exceptions import TokenError

_password_hasher = PasswordHash(
    (
        Argon2Hasher(
            time_cost=settings.ARGON2_TIME_COST,
            memory_cost=settings.ARGON2_MEMORY_COST,
            parallelism=settings.ARGON2_PARALLELISM,
        ),
    )
)


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: str
    type: TokenType
    jti: str
    iat: int
    exp: int


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hasher.verify(password, hashed)


def verify_and_update_password(password: str, hashed: str) -> tuple[bool, str | None]:
    """Returns ``(is_valid, new_hash_or_None)``.

    A non-None hash means the stored hash used outdated parameters and should be
    replaced (transparent rehashing on login).
    """
    return _password_hasher.verify_and_update(password, hashed)


def hash_token(token: str) -> str:
    """Deterministic digest used to store refresh tokens at rest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------
def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> IssuedToken:
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    jti = uuid.uuid4().hex
    claims: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if extra_claims:
        claims.update(extra_claims)
    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return IssuedToken(token=token, jti=jti, expires_at=expires_at)


def create_access_token(subject: str) -> IssuedToken:
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str) -> IssuedToken:
    return _create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> TokenPayload:
    try:
        raw = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("The token has expired.", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("The token is invalid.") from exc

    try:
        payload = TokenPayload.model_validate(raw)
    except ValidationError as exc:
        raise TokenError("The token is invalid.") from exc

    if expected_type is not None and payload.type is not expected_type:
        raise TokenError(f"Expected a {expected_type.value} token.")
    return payload
