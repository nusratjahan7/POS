"""Branch authorization.

The single place that answers "which branches may this user see and act on?".

Every branch-scoped read is *filtered* by the caller's scope and every
branch-scoped write is *asserted* against it. The scope is derived once per
request (see ``app.api.deps.get_branch_scope``) and shared by every endpoint, so
the rule lives in exactly one place.

Decisions (MODULE 22):
* "All branches" is a grant — the ``branches:all`` permission — held by the
  built-in Administrator role; superusers bypass as everywhere.
* A user with no explicit assignment falls back to their primary ``branch_id``,
  and, if that is unset, to the first active branch — preserving the
  single-branch behaviour of earlier modules.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.core.permissions import PermissionCode
from app.models.branch import Branch
from app.models.user import User


@dataclass(frozen=True, slots=True)
class BranchScope:
    """The branches a user may access.

    ``all_branches`` short-circuits every check; when it is set ``allowed`` is
    empty (there is nothing to enumerate). Otherwise ``allowed`` is the explicit
    set the user is restricted to.
    """

    all_branches: bool
    allowed: tuple[uuid.UUID, ...]

    def allows(self, branch_id: uuid.UUID) -> bool:
        return self.all_branches or branch_id in self.allowed


async def resolve_branch_scope(session: AsyncSession, user: User) -> BranchScope:
    """Derive a user's branch scope. Called once per request."""
    if user.is_superuser or user.has_permission(PermissionCode.BRANCHES_ALL.value):
        return BranchScope(all_branches=True, allowed=())

    assigned = tuple(
        dict.fromkeys(
            branch.id
            for branch in user.branches
            if not branch.is_deleted and branch.is_active
        )
    )
    if assigned:
        return BranchScope(all_branches=False, allowed=assigned)

    if user.branch_id is not None:
        return BranchScope(all_branches=False, allowed=(user.branch_id,))

    first = (
        await session.execute(
            select(Branch.id)
            .where(Branch.deleted_at.is_(None), Branch.is_active.is_(True))
            .order_by(Branch.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return BranchScope(all_branches=False, allowed=(first,) if first is not None else ())


def scoped_branch_ids(
    scope: BranchScope, requested: uuid.UUID | None
) -> list[uuid.UUID] | None:
    """Translate a request's optional ``branch_id`` into a list filter.

    * an explicit, allowed ``branch_id`` narrows to that one branch;
    * an explicit, forbidden ``branch_id`` is a 403 (never a silent empty list);
    * no ``branch_id`` with full access means *no restriction* (``None``);
    * no ``branch_id`` for a scoped user means *their* branches only.
    """
    if requested is not None:
        if not scope.allows(requested):
            raise ForbiddenError(
                "You do not have access to that branch.",
                code="branch_forbidden",
                details=[{"field": "branch_id", "message": "Not one of your branches."}],
            )
        return [requested]
    if scope.all_branches:
        return None
    return list(scope.allowed)


def assert_branch_allowed(scope: BranchScope, branch_id: uuid.UUID | None) -> None:
    """Enforce scope on a write. ``None`` is a no-op (nothing to check)."""
    if branch_id is None:
        return
    if not scope.allows(branch_id):
        raise ForbiddenError(
            "You do not have access to that branch.",
            code="branch_forbidden",
            details=[{"field": "branch_id", "message": "Not one of your branches."}],
        )
