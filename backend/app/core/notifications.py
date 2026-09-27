"""Outbound notification delivery.

There is no mail transport in this module yet, so the default notifier writes
the actionable link to the application log. That keeps the forgot-password flow
end-to-end usable in development without shipping a fake mailer.

Swapping in a real provider means implementing :class:`Notifier` and assigning
``notifier``; callers depend on the protocol, never on the transport.

Security note: the link is treated as a bearer secret, so it is only logged
outside production. In production an unconfigured transport logs the *fact* of a
request, never the token.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Protocol

from app.core.config import settings
from app.models.user import User


class Notifier(Protocol):
    def send_password_reset(
        self,
        *,
        user: User,
        reset_url: str,
        expires_at: datetime,
    ) -> None: ...


class LoggingNotifier:
    """Development transport: the reset link goes to the log, not to an inbox."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("app.notifications")

    def send_password_reset(
        self,
        *,
        user: User,
        reset_url: str,
        expires_at: datetime,
    ) -> None:
        if settings.is_production:
            self.logger.warning(
                "Password reset requested for %s but no mail transport is configured; "
                "the link was not delivered.",
                user.email,
            )
            return
        self.logger.info(
            "Password reset for %s (expires %s): %s",
            user.email,
            expires_at.isoformat(),
            reset_url,
        )


notifier: Notifier = LoggingNotifier()
