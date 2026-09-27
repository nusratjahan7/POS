"""Reusable, non-HTTP input validators."""

from __future__ import annotations

import re

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def validate_password_strength(value: str) -> str:
    """Enforce the shared password policy.

    Policy: 8-128 chars, at least one letter, one digit and one symbol. Kept
    modest and centralised so login and admin flows agree.
    """
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(value) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
    if not any(char.isalpha() for char in value):
        raise ValueError("Password must contain at least one letter.")
    if not any(char.isdigit() for char in value):
        raise ValueError("Password must contain at least one digit.")
    if _SPECIAL.search(value) is None:
        raise ValueError("Password must contain at least one symbol.")
    return value
