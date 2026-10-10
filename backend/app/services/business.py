"""Business (organisation) settings.

The business is a singleton in this deployment: :meth:`BusinessService.get`
returns the one active row, creating a default on first access so the settings
screen always has something to edit. The columns are modelled for many
businesses so a future multi-tenant move is a data migration only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import PermissionCode
from app.models.business import Business
from app.repositories.business import BusinessRepository
from app.schemas.business import BusinessUpdate
from app.services.audit_log import AuditLogService
from app.services.notification import NotificationService

DEFAULT_BUSINESS_NAME = "My Business"


def _snapshot(business: Business) -> dict[str, Any]:
    """The editable business settings, for the audit log."""
    return {
        "name": business.name,
        "currency": business.currency,
        "timezone": business.timezone,
        "tax_enabled": business.tax_enabled,
        "tax_inclusive": business.tax_inclusive,
        "tax_label": business.tax_label,
        "default_tax_rate": business.default_tax_rate,
        "is_active": business.is_active,
    }


class BusinessService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.businesses = BusinessRepository(session)

    async def get(self) -> Business:
        """Return the current business, creating the default if none exists."""
        business = await self.businesses.get_default()
        if business is None:
            business = Business(
                name=DEFAULT_BUSINESS_NAME,
                currency="USD",
                timezone="UTC",
            )
            await self.businesses.add(business)
            await self.session.commit()
        return business

    async def update(self, payload: BusinessUpdate) -> Business:
        business = await self.get()
        before = _snapshot(business)
        provided = payload.model_fields_set

        if payload.name is not None:
            business.name = payload.name.strip()

        # Nullable text fields are cleared by sending an explicit null.
        for field in ("logo_url", "phone", "email", "address"):
            if field in provided:
                value = getattr(payload, field)
                setattr(business, field, str(value) if value is not None else None)

        if payload.currency is not None:
            business.currency = payload.currency
        if payload.timezone is not None:
            business.timezone = payload.timezone
        if payload.tax_enabled is not None:
            business.tax_enabled = payload.tax_enabled
        if payload.tax_inclusive is not None:
            business.tax_inclusive = payload.tax_inclusive
        if "tax_label" in provided and payload.tax_label is not None:
            business.tax_label = payload.tax_label.strip()
        if payload.default_tax_rate is not None:
            business.default_tax_rate = payload.default_tax_rate
        if payload.is_active is not None:
            business.is_active = payload.is_active

        after = _snapshot(business)
        AuditLogService(self.session).record(
            action="settings.business.update",
            module="settings",
            entity="business",
            entity_id=business.id,
            old=before,
            new=after,
        )
        await NotificationService(self.session).push_to_permission(
            PermissionCode.SETTINGS_MANAGE.value,
            type="system",
            severity="info",
            title="Business settings updated",
            entity_type="business",
            entity_id=business.id,
            data={"name": after["name"], "currency": after["currency"]},
        )

        await self.session.commit()
        return business
