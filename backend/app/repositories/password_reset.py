from __future__ import annotations

import uuid

from sqlalchemy import func, select, update

from app.models.password_reset import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def invalidate_outstanding(self, user_id: uuid.UUID) -> int:
        """Consume every unused token for a user.

        Called before issuing a new link (so only the newest works) and again
        after a successful reset (so nothing else can be replayed).
        """
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=func.now())
            .execution_options(synchronize_session="fetch")
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
