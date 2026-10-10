"""Stock transfer endpoints — the branch-to-branch workflow.

Reading needs ``transfers:read``. Each workflow step has its own permission:
``transfers:write`` (create/edit/request/cancel), ``transfers:approve``,
``transfers:ship`` and ``transfers:receive``. Only ship and receive touch stock,
and they do so inside ``TransferService`` in one transaction.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import BranchScopeDep, CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.stock_transfer import StockTransferRepository
from app.schemas.common import Page
from app.schemas.transfer import (
    TransferCancel,
    TransferCreate,
    TransferRead,
    TransferStatus,
    TransferSummary,
    TransferUpdate,
)
from app.services.branch_access import (
    assert_any_branch_allowed,
    assert_branch_allowed,
    scoped_branch_ids,
)
from app.services.transfer import TransferService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.get(
    "",
    response_model=Page[TransferSummary],
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_READ))],
)
async def list_transfers(
    session: SessionDep,
    scope: BranchScopeDep,
    params: Pagination,
    search: Annotated[
        str | None, Query(max_length=32, description="Transfer number or reference")
    ] = None,
    transfer_status: Annotated[TransferStatus | None, Query(alias="status")] = None,
    branch_id: Annotated[uuid.UUID | None, Query(description="Either side of the transfer")] = None,
    from_branch_id: Annotated[uuid.UUID | None, Query()] = None,
    to_branch_id: Annotated[uuid.UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query(description="Created on or after")] = None,
    date_to: Annotated[date | None, Query(description="Created on or before")] = None,
    sort: Annotated[str | None, Query(description="e.g. -created_at, transfer_number")] = None,
) -> Page[TransferSummary]:
    if from_branch_id is not None:
        assert_branch_allowed(scope, from_branch_id)
    if to_branch_id is not None:
        assert_branch_allowed(scope, to_branch_id)

    transfers, total = await TransferService(session).list_transfers(
        params,
        sort=parse_sort(sort, StockTransferRepository.SORTABLE, default="-created_at"),
        search=search,
        status=transfer_status,
        branch_ids=scoped_branch_ids(scope, branch_id),
        from_branch_id=from_branch_id,
        to_branch_id=to_branch_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Page.build(
        [TransferSummary.model_validate(transfer) for transfer in transfers],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "",
    response_model=TransferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Raise a stock transfer",
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_WRITE))],
)
async def create_transfer(
    session: SessionDep, actor: CurrentUser, scope: BranchScopeDep, payload: TransferCreate
) -> TransferRead:
    assert_branch_allowed(scope, payload.from_branch_id)
    transfer = await TransferService(session).create(payload, actor_id=actor.id)
    return TransferRead.model_validate(transfer)


@router.get(
    "/{transfer_id}",
    response_model=TransferRead,
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_READ))],
)
async def get_transfer(
    session: SessionDep, scope: BranchScopeDep, transfer_id: uuid.UUID
) -> TransferRead:
    transfer = await TransferService(session).get_or_404(transfer_id)
    assert_any_branch_allowed(scope, transfer.from_branch_id, transfer.to_branch_id)
    return TransferRead.model_validate(transfer)


@router.patch(
    "/{transfer_id}",
    response_model=TransferRead,
    summary="Edit a draft transfer",
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_WRITE))],
)
async def update_transfer(
    session: SessionDep,
    scope: BranchScopeDep,
    transfer_id: uuid.UUID,
    payload: TransferUpdate,
) -> TransferRead:
    service = TransferService(session)
    existing = await service.get_or_404(transfer_id)
    assert_branch_allowed(scope, existing.from_branch_id)
    if payload.from_branch_id is not None:
        assert_branch_allowed(scope, payload.from_branch_id)
    return TransferRead.model_validate(await service.update(transfer_id, payload))


@router.post(
    "/{transfer_id}/request",
    response_model=TransferRead,
    summary="Submit a draft transfer for approval",
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_WRITE))],
)
async def request_transfer(
    session: SessionDep, actor: CurrentUser, scope: BranchScopeDep, transfer_id: uuid.UUID
) -> TransferRead:
    service = TransferService(session)
    transfer = await service.get_or_404(transfer_id)
    assert_branch_allowed(scope, transfer.from_branch_id)
    return TransferRead.model_validate(await service.request(transfer_id, actor_id=actor.id))


@router.post(
    "/{transfer_id}/approve",
    response_model=TransferRead,
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_APPROVE))],
)
async def approve_transfer(
    session: SessionDep, actor: CurrentUser, scope: BranchScopeDep, transfer_id: uuid.UUID
) -> TransferRead:
    service = TransferService(session)
    transfer = await service.get_or_404(transfer_id)
    assert_branch_allowed(scope, transfer.from_branch_id)
    return TransferRead.model_validate(await service.approve(transfer_id, actor_id=actor.id))


@router.post(
    "/{transfer_id}/ship",
    response_model=TransferRead,
    summary="Ship a transfer (decreases the source branch)",
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_SHIP))],
)
async def ship_transfer(
    session: SessionDep, actor: CurrentUser, scope: BranchScopeDep, transfer_id: uuid.UUID
) -> TransferRead:
    service = TransferService(session)
    transfer = await service.get_or_404(transfer_id)
    assert_branch_allowed(scope, transfer.from_branch_id)
    return TransferRead.model_validate(await service.ship(transfer_id, actor_id=actor.id))


@router.post(
    "/{transfer_id}/receive",
    response_model=TransferRead,
    summary="Receive a transfer (increases the destination branch)",
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_RECEIVE))],
)
async def receive_transfer(
    session: SessionDep, actor: CurrentUser, scope: BranchScopeDep, transfer_id: uuid.UUID
) -> TransferRead:
    service = TransferService(session)
    transfer = await service.get_or_404(transfer_id)
    assert_branch_allowed(scope, transfer.to_branch_id)
    return TransferRead.model_validate(await service.receive(transfer_id, actor_id=actor.id))


@router.post(
    "/{transfer_id}/cancel",
    response_model=TransferRead,
    summary="Cancel a transfer that has not shipped",
    dependencies=[Depends(require_permissions(PermissionCode.TRANSFERS_WRITE))],
)
async def cancel_transfer(
    session: SessionDep,
    actor: CurrentUser,
    scope: BranchScopeDep,
    transfer_id: uuid.UUID,
    payload: TransferCancel | None = None,
) -> TransferRead:
    service = TransferService(session)
    transfer = await service.get_or_404(transfer_id)
    assert_branch_allowed(scope, transfer.from_branch_id)
    reason = payload.reason if payload else None
    return TransferRead.model_validate(
        await service.cancel(transfer_id, reason=reason, actor_id=actor.id)
    )
