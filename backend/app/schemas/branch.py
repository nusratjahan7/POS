from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class BranchBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    business_id: uuid.UUID | None = None


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    business_id: uuid.UUID | None = None


class BranchRead(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    address: str | None
    phone: str | None
    is_active: bool
    business_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class BranchSummary(ORMModel):
    id: uuid.UUID
    name: str
    code: str
