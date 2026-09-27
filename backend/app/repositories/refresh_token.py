from __future__ import annotations

import uuid

from sqlalchemy import func, select, update

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        *,
        except_token_id: uuid.UUID | None = None,
    ) -> int:
        """Revoke every outstanding token for a user (e.g. on password change)."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
            .execution_options(synchronize_session="fetch")
        )
        if except_token_id is not None:
            stmt = stmt.where(RefreshToken.id != except_token_id)
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
