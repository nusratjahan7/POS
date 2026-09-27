"""Security audit log.

A dedicated ``app.audit`` logger for authentication / authorization events.
Every field is passed through :func:`app.core.logging.redact` first, so a
password, hash or token can never reach the log even if a caller passes one by
mistake. Requests are correlated by the existing request-id filter.

This is a *log* — not a database table. Persisting audit events is a separate
concern (see the plan's out-of-scope section).
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.logging import redact

logger = logging.getLogger("app.audit")


def audit(event: str, **fields: Any) -> None:
    """Record a security event. Never include secrets in ``fields``."""
    safe = redact(fields)
    detail = " ".join(f"{key}={value}" for key, value in safe.items())
    logger.info("event=%s%s", event, f" {detail}" if detail else "")
