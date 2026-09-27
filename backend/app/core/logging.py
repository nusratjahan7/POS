"""Logging configuration.

A request id is propagated through a contextvar so every log line emitted while
handling a request can be correlated. Sensitive fields are never logged.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

from app.core.config import settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_REDACTED = "***redacted***"
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "hashed_password",
        "new_password",
        "current_password",
        "access_token",
        "refresh_token",
        "authorization",
        "token",
        "secret",
        "secret_key",
    }
)


def new_request_id() -> str:
    return uuid.uuid4().hex


def redact(data: dict[str, object]) -> dict[str, object]:
    """Return a copy of ``data`` with sensitive values masked."""
    return {
        key: (_REDACTED if key.lower() in _SENSITIVE_KEYS else value) for key, value in data.items()
    }


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def configure_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Uvicorn's access log duplicates our request logging; keep its errors only.
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False
    for noisy in ("sqlalchemy.engine", "asyncpg"):
        logging.getLogger(noisy).setLevel(logging.WARNING if not settings.DB_ECHO else logging.INFO)
