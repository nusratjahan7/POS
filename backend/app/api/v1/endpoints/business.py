"""Business (organisation) settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.schemas.business import BusinessRead, BusinessUpdate
from app.services.business import BusinessService

router = APIRouter(prefix="/business", tags=["business"])


@router.get(
    "",
    response_model=BusinessRead,
    summary="The business profile, currency and tax settings",
    dependencies=[Depends(require_permissions(PermissionCode.BUSINESS_READ))],
)
async def get_business(session: SessionDep) -> BusinessRead:
    return BusinessRead.model_validate(await BusinessService(session).get())


@router.patch(
    "",
    response_model=BusinessRead,
    summary="Update the business profile and tax settings",
    dependencies=[Depends(require_permissions(PermissionCode.BUSINESS_WRITE))],
)
async def update_business(session: SessionDep, payload: BusinessUpdate) -> BusinessRead:
    return BusinessRead.model_validate(await BusinessService(session).update(payload))
