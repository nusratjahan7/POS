"""Sales: the till's one write path, and the only place stock leaves a branch.

Completing a sale is a single transaction that touches five tables. Every figure
— unit price, line totals, discount, tax and the grand total — is computed here
from the database, never accepted from the client. Stock leaves through
:class:`~app.services.inventory.InventoryService`, which locks each
``(product, branch)`` row and refuses to go below zero, so two tills selling the
same last unit cannot both succeed.

If any step fails the whole thing is rolled back: no sale, no items, no payments,
no movements, no balance change.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.business import Business
from app.models.customer import Customer
from app.models.register import Register
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.repositories.branch import BranchRepository
from app.repositories.business import BusinessRepository
from app.repositories.customer import CustomerRepository
from app.repositories.payment_method import PaymentMethodRepository
from app.repositories.register import RegisterRepository
from app.repositories.sale import SaleRepository
from app.schemas.discount import DiscountLineInput
from app.schemas.sale import SaleCreate, SalePaymentCreate
from app.services.customer import CustomerService
from app.services.discount import DiscountService
from app.services.inventory import InventoryService
from app.services.register_session import RegisterSessionService
from app.utils.money import ZERO, money
from app.utils.pagination import PageParams

HUNDRED = Decimal("100")


class SaleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sales = SaleRepository(session)
        self.branches = BranchRepository(session)
        self.business = BusinessRepository(session)
        self.customers = CustomerRepository(session)
        self.methods = PaymentMethodRepository(session)
        self.registers = RegisterRepository(session)
        self.inventory = InventoryService(session)
        self.credit = CustomerService(session)
        self.cash = RegisterSessionService(session)
        self.discounts = DiscountService(session)

    # --- Reads -------------------------------------------------------------
    def _detail_query(self, sale_id: uuid.UUID) -> Any:
        return (
            select(Sale)
            .where(Sale.id == sale_id)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
        )

    async def get_or_404(self, sale_id: uuid.UUID) -> Sale:
        sale = (await self.session.execute(self._detail_query(sale_id))).scalars().one_or_none()
        if sale is None:
            raise NotFoundError("Sale not found.", code="sale_not_found")
        return sale

    async def _reload(self, sale_id: uuid.UUID) -> Sale:
        stmt = self._detail_query(sale_id).execution_options(populate_existing=True)
        return (await self.session.execute(stmt)).scalars().one()

    async def list_sales(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Sale], int]:
        return await self.sales.list_sales(params, sort=sort, **filters)

    async def list_cashiers(self) -> Sequence[tuple[uuid.UUID, str]]:
        """Cashiers who have sales, for the management screen's filter."""
        return await self.sales.cashiers()

    async def receipt(self, sale_id: uuid.UUID) -> dict[str, Any]:
        """A sale plus the business details a printed receipt needs."""
        sale = await self.get_or_404(sale_id)
        business = await self.business.get_default()
        if business is None:
            raise NotFoundError(
                "The business profile is not configured yet.", code="business_not_configured"
            )
        return {"business": business, "branch": sale.branch, "sale": sale}

    # --- Internals ---------------------------------------------------------
    async def _unique_number(self) -> str:
        for _ in range(6):
            candidate = f"INV-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"
            if not await self.sales.number_exists(candidate):
                return candidate
        raise ConflictError(
            "Could not allocate an invoice number, please try again.",
            code="sale_number_conflict",
        )

    async def _resolve_branch(self, branch_id: uuid.UUID) -> Any:
        branch = await self.branches.get(branch_id)
        if branch is None or branch.is_deleted:
            raise UnprocessableError(
                "The selected branch does not exist.",
                code="unknown_branch",
                details=[{"field": "branch_id", "message": "Unknown branch."}],
            )
        return branch

    async def _resolve_customer(self, customer_id: uuid.UUID | None) -> Customer | None:
        if customer_id is None:
            return None
        customer = await self.customers.get(customer_id)
        if customer is None or customer.is_deleted:
            raise UnprocessableError(
                "The selected customer does not exist.",
                code="unknown_customer",
                details=[{"field": "customer_id", "message": "Unknown customer."}],
            )
        return customer

    async def _validate_register(self, register_id: uuid.UUID, branch_id: uuid.UUID) -> Register:
        register = await self.registers.get(register_id)
        if register is None or register.is_deleted:
            raise UnprocessableError(
                "The selected register does not exist.",
                code="unknown_register",
                details=[{"field": "register_id", "message": "Unknown register."}],
            )
        if register.branch_id != branch_id:
            raise UnprocessableError(
                "That register belongs to a different branch.",
                code="register_branch_mismatch",
                details=[{"field": "register_id", "message": "Wrong branch."}],
            )
        return register

    def _tax_for(self, net: Decimal, business: Business | None) -> Decimal:
        """Tax on the discounted net, following the business's settings.

        Mirrors the till's own preview arithmetic so the two never disagree.
        """
        if business is None or not business.tax_enabled or business.default_tax_rate <= 0:
            return ZERO
        rate = business.default_tax_rate / HUNDRED
        if business.tax_inclusive:
            # The shelf price already contains the tax; extract the embedded part.
            return money(net - net / (1 + rate))
        return money(net * rate)

    async def _build_payments(
        self, rows: Sequence[SalePaymentCreate]
    ) -> tuple[list[SalePayment], Decimal, Decimal, Decimal]:
        """Validate each tender and total what it applies, returns and pays in cash."""
        payments: list[SalePayment] = []
        applied = ZERO
        change = ZERO
        cash_taken = ZERO

        for row in rows:
            method = await self.methods.get(row.payment_method_id)
            if method is None or method.is_deleted or not method.is_active:
                raise UnprocessableError(
                    "A selected payment method is not available.",
                    code="unknown_payment_method",
                    details=[{"field": "payments", "message": "Unavailable payment method."}],
                )
            if method.requires_reference and not (row.reference or "").strip():
                raise UnprocessableError(
                    f"{method.name} needs a reference.",
                    code="payment_reference_required",
                    details=[
                        {
                            "field": "payments",
                            "message": f"A reference is required for {method.name}.",
                        }
                    ],
                )

            amount = money(row.amount)
            tendered = money(row.tendered) if row.tendered is not None else None
            if tendered is not None and tendered < amount:
                raise UnprocessableError(
                    "The amount received cannot be less than the amount applied.",
                    code="tendered_below_amount",
                    details=[{"field": "payments", "message": "Received less than applied."}],
                )

            given = (tendered - amount) if tendered is not None else ZERO
            payments.append(
                SalePayment(
                    payment_method_id=method.id,
                    amount=amount,
                    tendered=tendered,
                    change_given=given,
                    reference=row.reference,
                    note=row.note,
                )
            )
            applied += amount
            change += given
            if method.opens_cash_drawer:
                cash_taken += amount

        return payments, money(applied), money(change), money(cash_taken)

    # --- Commands ----------------------------------------------------------
    async def create(self, payload: SaleCreate, *, actor_id: uuid.UUID | None = None) -> Sale:
        """Complete a sale: validate, price, tender, move stock, settle credit.

        All of it in one transaction, in the order the spec lays out. Nothing is
        committed until every step has succeeded, so a failure at any point leaves
        the database exactly as it was.
        """
        branch = await self._resolve_branch(payload.branch_id)
        customer = await self._resolve_customer(payload.customer_id)
        business = await self.business.get_default()

        # Every sale is rung against an open till: the register must exist and
        # belong to this branch, and its session must be open.
        register = await self._validate_register(payload.register_id, branch.id)
        cash_session = await self.cash.require_open(register.id)

        # Pricing — unit prices, promotions, the coupon and any manual discount —
        # is the discount engine's job. The client's figures are never trusted.
        pricing = await self.discounts.price(
            [
                DiscountLineInput(
                    product_id=row.product_id, quantity=row.quantity, discount=row.discount
                )
                for row in payload.items
            ],
            customer_id=payload.customer_id,
            coupon_code=payload.coupon_code,
            order_discount=payload.order_discount,
        )
        items = [
            SaleItem(
                product_id=line.product_id,
                product_name=line.product_name,
                sku=line.sku,
                unit=line.unit,
                quantity=line.quantity,
                unit_price=line.unit_price,
                discount=line.discount,
                subtotal=line.subtotal,
                line_total=line.line_total,
            )
            for line in pricing.lines
        ]
        subtotal = pricing.subtotal
        discount = pricing.total_discount

        net = pricing.net
        tax = self._tax_for(net, business)
        inclusive = bool(business and business.tax_enabled and business.tax_inclusive)
        total = net if inclusive else money(net + tax)

        payments, applied, change, cash_taken = await self._build_payments(payload.payments)

        if applied > total:
            raise UnprocessableError(
                f"The payments add up to more than the {total} total. "
                "Record anything extra as the amount received, not as payment.",
                code="payments_exceed_total",
                details=[{"field": "payments", "message": "Greater than the total."}],
            )

        due = money(total - applied)
        if due > 0 and customer is None:
            raise UnprocessableError(
                "An unpaid balance needs a customer to carry it on their account.",
                code="credit_sale_requires_customer",
                details=[{"field": "customer_id", "message": "Required for a sale on account."}],
            )
        if change > 0 and due > 0:
            raise UnprocessableError(
                "There is no change on a sale that still has a balance due.",
                code="change_on_unpaid_sale",
                details=[{"field": "payments", "message": "Unpaid sale with change given."}],
            )

        # The id is allocated up front so items, payments and stock movements can
        # reference the sale before anything is flushed.
        sale = Sale(
            id=uuid.uuid4(),
            sale_number=await self._unique_number(),
            branch=branch,
            register_id=register.id,
            customer=customer,
            cashier_id=actor_id,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total,
            paid=applied,
            due=due,
            change_amount=change,
            status="completed",
            note=payload.note,
        )
        for item in items:
            item.sale_id = sale.id
        for payment in payments:
            payment.sale_id = sale.id
            payment.user_id = actor_id
        sale.items = items
        sale.payments = payments
        self.session.add(sale)

        try:
            # Stock leaves the branch, one locked movement per line. Sorting by
            # product keeps concurrent tills from deadlocking on the row locks.
            for item in sorted(items, key=lambda row: row.product_id):
                await self.inventory.apply_movement(
                    product_id=item.product_id,
                    branch_id=branch.id,
                    quantity=-item.quantity,
                    movement_type="stock_out",
                    reference_type="sale",
                    reference_id=sale.id,
                    user_id=actor_id,
                    note=f"Sold on {sale.sale_number}",
                )

            # Anything still owed becomes a receivable on the customer's account.
            # Staged, not committed — it lands with this sale or not at all.
            if due > 0 and customer is not None:
                await self.credit.charge_credit(customer.id, due)

            # Cash applied goes into the open drawer (the tendered amount less any
            # change already handed back). Staged with the sale.
            if cash_taken > 0:
                await self.cash.record_cash(
                    cash_session.id,
                    cash_taken,
                    movement_type="sale",
                    reference_type="sale",
                    reference_id=sale.id,
                    user_id=actor_id,
                    note=f"Cash on {sale.sale_number}",
                )

            # What each promotion/coupon actually gave, for the receipt and for
            # usage-limit counting.
            if pricing.applied:
                self.session.add_all(
                    self.discounts.redemption_rows(
                        pricing,
                        sale_id=sale.id,
                        customer_id=customer.id if customer is not None else None,
                    )
                )

            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self._reload(sale.id)
