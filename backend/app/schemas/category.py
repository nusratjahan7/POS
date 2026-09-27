from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=500)
    parent_id: uuid.UUID | None = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """`slug` is derived from the name; clients never set it."""


class CategoryUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched.

    `parent_id` is nullable on purpose: sending an explicit ``null`` promotes the
    category to the top level. Detection uses ``model_fields_set``.
    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=500)
    parent_id: uuid.UUID | None = None
    is_active: bool | None = None


class CategoryRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    image_url: str | None
    parent_id: uuid.UUID | None
    parent: CategorySummary | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CategorySummary(ORMModel):
    id: uuid.UUID
    name: str
    slug: str


class CategoryNode(ORMModel):
    """A category with its descendants, used to render the hierarchy."""

    id: uuid.UUID
    name: str
    slug: str
    image_url: str | None
    parent_id: uuid.UUID | None
    is_active: bool
    children: list[CategoryNode] = Field(default_factory=list)


CategoryNode.model_rebuild()
