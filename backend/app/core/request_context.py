"""Request-scoped context for audit metadata.

Mirrors ``app.core.logging.request_id_ctx``: request-wide values are set once (the
middleware supplies the client IP and user-agent, the auth dependency supplies the
actor) and read by the service layer. That lets an audit row record *who* and *from
where* without threading an IP argument through every service signature.

Starlette runs the downstream app in its own task, so a value set inside a request
never leaks into another one.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

client_ip_ctx: ContextVar[str | None] = ContextVar("client_ip", default=None)
user_agent_ctx: ContextVar[str | None] = ContextVar("user_agent", default=None)
current_user_id_ctx: ContextVar[uuid.UUID | None] = ContextVar("current_user_id", default=None)


def set_request_meta(
    *, client_ip: str | None, user_agent: str | None
) -> tuple[Token[str | None], Token[str | None]]:
    return client_ip_ctx.set(client_ip), user_agent_ctx.set(user_agent)


def reset_request_meta(tokens: tuple[Token[str | None], Token[str | None]]) -> None:
    client_ip_ctx.reset(tokens[0])
    user_agent_ctx.reset(tokens[1])


def set_current_user(user_id: uuid.UUID | None) -> Token[uuid.UUID | None]:
    return current_user_id_ctx.set(user_id)
