from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

NotificationType = Literal[
    "low_stock",
    "out_of_stock",
    "customer_due",
    "supplier_due",
    "new_sale",
    "refund",
    "system",
]

NotificationSeverity = Literal["info", "warning", "critical"]


class NotificationRead(ORMModel):
    id: uuid.UUID
    type: str
    severity: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: str | None
    data: dict[str, Any] | None
    read_at: datetime | None
    created_at: datetime


class NotificationUnread(BaseModel):
    """The caller's unread count — the number on the bell."""

    unread: int = Field(ge=0)
