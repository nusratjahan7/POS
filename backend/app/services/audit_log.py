"""Persisted audit log.

``app.core.audit`` remains the *log-only* audit helper. This service is its
database counterpart: it stages an :class:`~app.models.audit_log.AuditLog` row for
every sensitive action, in the caller's own transaction, so the entry lands if and
only if the action it describes lands.

Two safety rules are enforced here, not at the call sites:

* **Deep redaction** — any key whose name looks like a credential (password, token,
  secret, authorization, …) is masked at any nesting depth, so a caller cannot leak
  one by accident.
* **Serialisation** — UUIDs, ``Decimal``, datetimes and enums are converted to
  primitives so every value is JSONB-safe.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.request_context import client_ip_ctx, current_user_id_ctx, user_agent_ctx
from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.utils.jsonable import jsonable
from app.utils.pagination import PageParams

_REDACTED = "***redacted***"
#: A key is sensitive if its lower-cased name contains any of these fragments.
_SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "authorization",
    "hashed",
    "credential",
    "otp",
    "pin",
)

USER_AGENT_MAX_LENGTH = 255


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS)


def redact(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Mask sensitive keys (at any depth) in a snapshot before it is stored."""
    if data is None:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if _is_sensitive(str(key)):
            cleaned[key] = _REDACTED
        elif isinstance(value, dict):
            cleaned[key] = redact(value)
        elif isinstance(value, (list, tuple, set, frozenset)):
            cleaned[key] = [redact(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned[key] = value
    return cleaned


class AuditLogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logs = AuditLogRepository(session)

    # --- Writes ------------------------------------------------------------
    def record(
        self,
        *,
        action: str,
        module: str,
        entity: str | None = None,
        entity_id: str | uuid.UUID | None = None,
        old: dict[str, Any] | None = None,
        new: dict[str, Any] | None = None,
        actor: User | None = None,
        user_id: uuid.UUID | None = None,
        user_email: str | None = None,
        user_name: str | None = None,
    ) -> AuditLog:
        """Stage an audit row; the caller's transaction commits it.

        The actor defaults to the request's authenticated user (via context) and the
        client IP / user-agent are read from the request context, so call sites do
        not have to thread them through. Pass ``user_id``/``user_email`` explicitly
        for events with no authenticated actor (e.g. a failed sign-in).
        """
        actor_id = actor.id if actor is not None else user_id
        if actor_id is None:
            actor_id = current_user_id_ctx.get()

        user_agent = user_agent_ctx.get()
        entry = AuditLog(
            user_id=actor_id,
            user_email=actor.email if actor is not None else user_email,
            user_name=actor.full_name if actor is not None else user_name,
            action=action,
            module=module,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_data=jsonable(redact(old)),
            new_data=jsonable(redact(new)),
            ip_address=client_ip_ctx.get(),
            user_agent=user_agent[:USER_AGENT_MAX_LENGTH] if user_agent else None,
        )
        self.session.add(entry)
        return entry

    # --- Reads -------------------------------------------------------------
    async def list_logs(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[AuditLog], int]:
        return await self.logs.list_logs(params, sort=sort, **filters)

    async def get_or_404(self, log_id: uuid.UUID) -> AuditLog:
        entry = await self.logs.get(log_id)
        if entry is None:
            raise NotFoundError("Audit entry not found.", code="audit_log_not_found")
        return entry
