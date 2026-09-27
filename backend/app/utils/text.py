from __future__ import annotations


def normalize_email(email: str) -> str:
    """Canonical stored/looked-up form of an email address.

    Applied on both write and read paths so uniqueness and lookups agree without
    relying on a functional index.
    """
    return email.strip().lower()


def normalize_code(code: str) -> str:
    return code.strip().upper()


def like_pattern(value: str) -> str:
    """Build a contains-match ILIKE pattern, neutralising wildcard characters."""
    escaped = value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
