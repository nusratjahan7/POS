from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator

from app.schemas.branch import BranchSummary
from app.schemas.common import ORMModel
from app.schemas.role import RoleRead, RoleSummary
from app.schemas.validators import validate_password_strength


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    branch_id: uuid.UUID | None = None


class UserCreate(UserBase):
    password: str
    role_ids: list[uuid.UUID] = Field(default_factory=list)
    # Only honoured when the caller is a superuser (enforced in the service).
    is_superuser: bool = False

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    branch_id: uuid.UUID | None = None
    role_ids: list[uuid.UUID] | None = None


class UserPasswordUpdate(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserRead(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None
    branch_id: uuid.UUID | None
    branch: BranchSummary | None
    roles: list[RoleRead]
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def permissions(self) -> list[str]:
        """Effective permission codes. ``["*"]`` denotes a superuser."""
        if self.is_superuser:
            return ["*"]
        codes: set[str] = set()
        for role in self.roles:
            codes.update(permission.code for permission in role.permissions)
        return sorted(codes)


class UserSummary(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None
    branch: BranchSummary | None
    roles: list[RoleSummary]
    created_at: datetime
