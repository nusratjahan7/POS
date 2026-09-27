from __future__ import annotations

import re
import unicodedata


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


_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(value: str, *, max_length: int = 200) -> str:
    """Turn a display name into a URL-safe slug.

    Accents are folded rather than dropped so "Café Crème" becomes
    ``cafe-creme`` instead of ``caf-cr-me``.
    """
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    slug = _NON_SLUG.sub("-", ascii_only.lower()).strip("-")
    return slug[:max_length].strip("-") or "item"
