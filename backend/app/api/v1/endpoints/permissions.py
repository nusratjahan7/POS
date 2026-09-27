"""Permission catalog endpoint (read-only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.schemas.role import PermissionRead
from app.services.role import RoleService

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get(
    "",
    response_model=list[PermissionRead],
    dependencies=[Depends(require_permissions(PermissionCode.ROLES_READ))],
)
async def list_permissions(session: SessionDep) -> list[PermissionRead]:
    permissions = await RoleService(session).list_permissions()
    return [PermissionRead.model_validate(permission) for permission in permissions]
