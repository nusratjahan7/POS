from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    user_email: str | None
    user_name: str | None
    action: str
    module: str
    entity: str | None
    entity_id: str | None
    old_data: dict[str, Any] | None
    new_data: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
