from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.product import Product
    from app.models.user import User

QUANTITY = Numeric(12, 3)

# Keep in lock-step with the CHECK constraint and the API Literal.
TRANSFER_STATUSES = ("draft", "requested", "approved", "shipped", "received", "cancelled")
_STATUSES_SQL = ", ".join(f"'{value}'" for value in TRANSFER_STATUSES)

#: Statuses a transfer can still be edited or cancelled from (before goods move).
PRE_SHIP_STATUSES = ("draft", "requested", "approved")


class StockTransfer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A stock transfer between two branches.

    The document moves through an explicit workflow — ``draft`` → ``requested``
    → ``approved`` → ``shipped`` → ``received`` (or ``cancelled`` before it
    ships). Stock only moves at two steps, both recorded by
    :class:`~app.services.inventory.InventoryService` in the same transaction as
    the status change:

    * **ship** decreases the source branch (a ``transfer_out`` movement);
    * **receive** increases the destination branch (a ``transfer_in`` movement).

    No other step touches inventory, so a transfer cannot lose or invent stock.
    """

    __tablename__ = "stock_transfers"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="valid_status"),
        CheckConstraint("from_branch_id <> to_branch_id", name="distinct_branches"),
    )

    transfer_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), server_default=text("'draft'"), nullable=False, index=True
    )

    from_branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    to_branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    reference: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(255))
    cancel_reason: Mapped[str | None] = mapped_column(String(255))

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    shipped_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    received_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    cancelled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    from_branch: Mapped[Branch] = relationship(
        lazy="joined", foreign_keys=[from_branch_id]
    )
    to_branch: Mapped[Branch] = relationship(lazy="joined", foreign_keys=[to_branch_id])
    created_by: Mapped[User | None] = relationship(
        lazy="joined", foreign_keys=[created_by_id]
    )
    requested_by: Mapped[User | None] = relationship(
        lazy="joined", foreign_keys=[requested_by_id]
    )
    approved_by: Mapped[User | None] = relationship(
        lazy="joined", foreign_keys=[approved_by_id]
    )
    shipped_by: Mapped[User | None] = relationship(
        lazy="joined", foreign_keys=[shipped_by_id]
    )
    received_by: Mapped[User | None] = relationship(
        lazy="joined", foreign_keys=[received_by_id]
    )
    cancelled_by: Mapped[User | None] = relationship(
        lazy="joined", foreign_keys=[cancelled_by_id]
    )

    items: Mapped[list[StockTransferLine]] = relationship(
        back_populates="transfer",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="StockTransferLine.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<StockTransfer {self.transfer_number} {self.status}>"


class StockTransferLine(Base, UUIDPrimaryKeyMixin):
    """One product and quantity on a transfer.

    ``product_name``/``sku`` are snapshots, so the document still reads correctly
    after a product is renamed.
    """

    __tablename__ = "stock_transfer_lines"
    __table_args__ = (
        UniqueConstraint(
            "transfer_id", "product_id", name="uq_stock_transfer_lines_transfer_id_product_id"
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    transfer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_transfers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    transfer: Mapped[StockTransfer] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<StockTransferLine {self.sku} {self.quantity}>"
