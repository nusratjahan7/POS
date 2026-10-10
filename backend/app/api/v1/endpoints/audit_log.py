"""Audit-log endpoints. Read-only, and gated by ``audit:read``."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_log import AuditLogRead
from app.schemas.common import Page
from app.services.audit_log import AuditLogService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get(
    "",
    response_model=Page[AuditLogRead],
    summary="The security audit log, newest first",
    dependencies=[Depends(require_permissions(PermissionCode.AUDIT_READ))],
)
async def list_audit_logs(
    session: SessionDep,
    params: Pagination,
    module: Annotated[str | None, Query(max_length=40)] = None,
    action: Annotated[str | None, Query(max_length=60)] = None,
    entity: Annotated[str | None, Query(max_length=40)] = None,
    entity_id: Annotated[str | None, Query(max_length=64)] = None,
    user_id: Annotated[uuid.UUID | None, Query(description="Filter by the actor")] = None,
    search: Annotated[
        str | None, Query(max_length=120, description="Action, module, entity or user")
    ] = None,
    date_from: Annotated[date | None, Query(description="On or after")] = None,
    date_to: Annotated[date | None, Query(description="On or before")] = None,
    sort: Annotated[str | None, Query(description="e.g. -created_at, action")] = None,
) -> Page[AuditLogRead]:
    logs, total = await AuditLogService(session).list_logs(
        params,
        sort=parse_sort(sort, AuditLogRepository.SORTABLE, default="-created_at"),
        module=module,
        action=action,
        entity=entity,
        entity_id=entity_id,
        user_id=user_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return Page.build(
        [AuditLogRead.model_validate(entry) for entry in logs],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogRead,
    dependencies=[Depends(require_permissions(PermissionCode.AUDIT_READ))],
)
async def get_audit_log(session: SessionDep, log_id: uuid.UUID) -> AuditLogRead:
    return AuditLogRead.model_validate(await AuditLogService(session).get_or_404(log_id))
