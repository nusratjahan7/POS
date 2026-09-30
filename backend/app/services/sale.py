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
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.business import Business
from app.models.customer import Customer
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.repositories.branch import BranchRepository
from app.repositories.business import BusinessRepository
from app.repositories.customer import CustomerRepository
from app.repositories.payment_method import PaymentMethodRepository
from app.repositories.product import ProductRepository
from app.repositories.register import RegisterRepository
from app.repositories.sale import SaleRepository
from app.schemas.sale import SaleCreate, SaleItemCreate, SalePaymentCreate
from app.services.customer import CustomerService
from app.services.inventory import InventoryService
from app.utils.pagination import PageParams

CENT = Decimal("0.01")
HUNDRED = Decimal("100")
ZERO = Decimal("0.00")


def money(value: Decimal) -> Decimal:
    """Round a computed amount to the currency's two decimal places."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class SaleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sales = SaleRepository(session)
        self.products = ProductRepository(session)
        self.branches = BranchRepository(session)
        self.business = BusinessRepository(session)
        self.customers = CustomerRepository(session)
        self.methods = PaymentMethodRepository(session)
        self.registers = RegisterRepository(session)
        self.inventory = InventoryService(session)
        self.credit = CustomerService(session)

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

    async def _validate_register(self, register_id: uuid.UUID, branch_id: uuid.UUID) -> None:
        register = await self.registers.get(register_id)
        if register is None:
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

    async def _build_items(self, rows: Sequence[SaleItemCreate]) -> tuple[list[SaleItem], Decimal]:
        """Price the basket server-side and snapshot what was sold."""
        seen: set[uuid.UUID] = set()
        items: list[SaleItem] = []
        subtotal = ZERO

        for row in rows:
            if row.product_id in seen:
                raise UnprocessableError(
                    "The same product appears twice on this sale.",
                    code="duplicate_sale_item",
                    details=[{"field": "items", "message": "Duplicate product."}],
                )
            seen.add(row.product_id)

            product = await self.products.get(row.product_id)
            if product is None or product.is_deleted or not product.is_active:
                raise UnprocessableError(
                    "A product on this sale is no longer available.",
                    code="unknown_product",
                    details=[
                        {"field": "items", "message": f"Unavailable product {row.product_id}."}
                    ],
                )

            unit_price = (
                product.discount_price
                if product.discount_price is not None
                else product.selling_price
            )
            unit_price = money(unit_price)
            line_subtotal = money(row.quantity * unit_price)
            discount = money(row.discount)
            if discount > line_subtotal:
                raise UnprocessableError(
                    f"The discount on {product.name} is more than the line total.",
                    code="discount_exceeds_line",
                    details=[{"field": "items", "message": "Line discount too large."}],
                )

            items.append(
                SaleItem(
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    unit=product.unit,
                    quantity=row.quantity,
                    unit_price=unit_price,
                    discount=discount,
                    subtotal=line_subtotal,
                    line_total=line_subtotal - discount,
                )
            )
            subtotal += line_subtotal

        return items, money(subtotal)

    async def _build_payments(
        self, rows: Sequence[SalePaymentCreate]
    ) -> tuple[list[SalePayment], Decimal, Decimal]:
        """Validate each tender and total what it applies and what it returns."""
        payments: list[SalePayment] = []
        applied = ZERO
        change = ZERO

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

        return payments, money(applied), money(change)

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
        if payload.register_id is not None:
            await self._validate_register(payload.register_id, branch.id)

        items, subtotal = await self._build_items(payload.items)

        # Discount: line discounts plus any order-level discount, never more than
        # the goods are worth.
        order_discount = money(payload.order_discount)
        line_discounts = sum((item.discount for item in items), ZERO)
        discount = money(line_discounts + order_discount)
        if discount > subtotal:
            raise UnprocessableError(
                "The discount cannot exceed the subtotal.",
                code="discount_exceeds_subtotal",
                details=[{"field": "order_discount", "message": "Greater than the subtotal."}],
            )

        net = money(subtotal - discount)
        tax = self._tax_for(net, business)
        inclusive = bool(business and business.tax_enabled and business.tax_inclusive)
        total = net if inclusive else money(net + tax)

        payments, applied, change = await self._build_payments(payload.payments)

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
            register_id=payload.register_id,
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

            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self._reload(sale.id)
