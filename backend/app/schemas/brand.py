from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class BrandBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class BrandCreate(BrandBase):
    """`slug` is derived from the name; clients never set it."""


class BrandUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class BrandRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BrandSummary(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
