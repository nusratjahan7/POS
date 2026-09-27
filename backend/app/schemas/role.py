from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PermissionRead(ORMModel):
    id: uuid.UUID
    code: str
    resource: str
    action: str
    description: str | None


class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=255)


class RoleCreate(RoleBase):
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=255)
    permission_codes: list[str] | None = None


class RoleRead(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionRead]
    created_at: datetime
    updated_at: datetime


class RoleSummary(ORMModel):
    id: uuid.UUID
    name: str
