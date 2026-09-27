from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel

# Percentage with three decimal places (e.g. 15.000), so half-percent VAT rates
# like 7.500 survive a round trip.
TaxRate = Decimal

CURRENCY_PATTERN = r"^[A-Za-z]{3}$"


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"'{value}' is not a recognised IANA time zone.") from exc
    return value


class BusinessBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    currency: str = Field(default="USD", pattern=CURRENCY_PATTERN)
    timezone: str = Field(default="UTC", max_length=64)
    tax_enabled: bool = False
    tax_inclusive: bool = True
    tax_label: str = Field(default="Tax", min_length=1, max_length=32)
    default_tax_rate: TaxRate = Field(
        default=Decimal("0"), ge=0, le=100, max_digits=6, decimal_places=3
    )
    is_active: bool = True

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        return _validate_timezone(value.strip())


class BusinessUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched."""

    name: str | None = Field(default=None, min_length=1, max_length=160)
    logo_url: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    currency: str | None = Field(default=None, pattern=CURRENCY_PATTERN)
    timezone: str | None = Field(default=None, max_length=64)
    tax_enabled: bool | None = None
    tax_inclusive: bool | None = None
    tax_label: str | None = Field(default=None, min_length=1, max_length=32)
    default_tax_rate: TaxRate | None = Field(
        default=None, ge=0, le=100, max_digits=6, decimal_places=3
    )
    is_active: bool | None = None

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else value

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str | None) -> str | None:
        return _validate_timezone(value.strip()) if value is not None else value


class BusinessRead(ORMModel):
    id: uuid.UUID
    name: str
    logo_url: str | None
    phone: str | None
    email: str | None
    address: str | None
    currency: str
    timezone: str
    tax_enabled: bool
    tax_inclusive: bool
    tax_label: str
    default_tax_rate: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
