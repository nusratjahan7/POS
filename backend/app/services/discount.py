"""The discount engine: promotions, coupons and the pricing of a basket.

Every figure here is computed from the database — the till only ever sends what
it wants to buy (products, quantities, any manual discount, and a coupon code),
and this module decides what that actually costs. Nothing a client computes is
trusted.

A single :class:`Discount` covers both kinds of promotion: one with a ``code`` is
a coupon the cashier must quote, one without is an automatic offer. Discounts
**stack**, each capped so a line or the basket can never go below zero.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.business import Business
from app.models.discount import Discount
from app.models.discount_redemption import DiscountRedemption
from app.repositories.brand import BrandRepository
from app.repositories.business import BusinessRepository
from app.repositories.category import CategoryRepository
from app.repositories.customer import CustomerRepository
from app.repositories.discount import DiscountRedemptionRepository, DiscountRepository
from app.repositories.product import ProductRepository
from app.repositories.sale import SaleRepository
from app.schemas.discount import (
    DiscountApplied,
    DiscountCreate,
    DiscountLineInput,
    DiscountLineResult,
    DiscountRead,
    DiscountUpdate,
    PriceBreakdown,
)
from app.utils.money import ZERO, money
from app.utils.pagination import PageParams
from app.utils.tax import tax_for, total_for

HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class _Line:
    product_id: uuid.UUID
    product_name: str
    sku: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    cost_price: Decimal
    subtotal: Decimal
    manual_discount: Decimal
    category_id: uuid.UUID | None
    brand_id: uuid.UUID | None
    has_discount_price: bool


@dataclass(frozen=True, slots=True)
class PricedLine:
    product_id: uuid.UUID
    product_name: str
    sku: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    cost_price: Decimal
    subtotal: Decimal
    manual_discount: Decimal
    automatic_discount: Decimal
    discount: Decimal
    line_total: Decimal


@dataclass(frozen=True, slots=True)
class AppliedDiscount:
    """A discount that actually contributed, with the amount it contributed."""

    discount_id: uuid.UUID | None
    code: str | None
    name: str
    amount: Decimal


@dataclass
class Pricing:
    lines: list[PricedLine]
    subtotal: Decimal
    line_discounts: Decimal
    cart_discount: Decimal
    coupon_discount: Decimal
    order_discount: Decimal
    total_discount: Decimal
    net: Decimal
    tax: Decimal
    total: Decimal
    coupon_code: str | None
    applied: list[AppliedDiscount] = field(default_factory=list)

    def breakdown(self) -> PriceBreakdown:
        """The API shape: same figures, grouped for display."""
        coupon = next((a for a in self.applied if a.code is not None), None)
        automatic = [a for a in self.applied if a.code is None]
        return PriceBreakdown(
            lines=[
                DiscountLineResult(
                    product_id=line.product_id,
                    automatic_discount=line.automatic_discount,
                    manual_discount=line.manual_discount,
                    discount=line.discount,
                    line_total=line.line_total,
                )
                for line in self.lines
            ],
            subtotal=self.subtotal,
            line_discounts=self.line_discounts,
            automatic_discount=money(self.cart_discount + sum((a.amount for a in automatic), ZERO)),
            coupon_discount=self.coupon_discount,
            order_discount=self.order_discount,
            total_discount=self.total_discount,
            net=self.net,
            tax=self.tax,
            total=self.total,
            coupon=(
                DiscountApplied(code=coupon.code, name=coupon.name, amount=coupon.amount)
                if coupon
                else None
            ),
            applied=[
                DiscountApplied(code=a.code, name=a.name, amount=a.amount) for a in self.applied
            ],
        )


class DiscountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.discounts = DiscountRepository(session)
        self.redemptions = DiscountRedemptionRepository(session)
        self.products = ProductRepository(session)
        self.categories = CategoryRepository(session)
        self.brands = BrandRepository(session)
        self.customers = CustomerRepository(session)
        self.sales = SaleRepository(session)
        self.business = BusinessRepository(session)

    # --- Reads -------------------------------------------------------------
    async def get_or_404(self, discount_id: uuid.UUID) -> Discount:
        # An explicit select (not `session.get`) so the targeting links are loaded
        # eagerly — `session.get` skips the `selectin` loaders and a later read
        # would trigger a lazy load outside the greenlet.
        stmt = (
            select(Discount)
            .where(Discount.id == discount_id)
            .execution_options(populate_existing=True)
        )
        discount = (await self.session.execute(stmt)).scalars().one_or_none()
        if discount is None or discount.is_deleted:
            raise NotFoundError("Discount not found.", code="discount_not_found")
        return discount

    async def list_discounts(
        self,
        params: PageParams,
        *,
        sort: tuple[object, bool] | None = None,
        **filters: object,
    ) -> tuple[Sequence[Discount], int]:
        return await self.discounts.list_discounts(params, sort=sort, **filters)

    def read(self, discount: Discount, *, redeemed_count: int = 0) -> DiscountRead:
        data = DiscountRead.model_validate(discount)
        return data.model_copy(
            update={
                "product_ids": sorted(discount.product_ids, key=str),
                "category_ids": sorted(discount.category_ids, key=str),
                "brand_ids": sorted(discount.brand_ids, key=str),
                "redeemed_count": redeemed_count,
            }
        )

    # --- Management --------------------------------------------------------
    async def create(self, payload: DiscountCreate) -> Discount:
        code = self._normalise_code(payload.code)
        if code is not None:
            await self._assert_code_free(code)
        self._assert_value(payload.scope, payload.type, payload.value)
        self._assert_window(payload.starts_at, payload.expires_at)
        await self._assert_targets(payload.product_ids, payload.category_ids, payload.brand_ids)

        discount = Discount(
            name=payload.name.strip(),
            code=code,
            scope=payload.scope,
            type=payload.type,
            value=money(payload.value),
            min_order_amount=money(payload.min_order_amount),
            max_discount_amount=(
                money(payload.max_discount_amount)
                if payload.max_discount_amount is not None
                else None
            ),
            starts_at=payload.starts_at,
            expires_at=payload.expires_at,
            usage_limit=payload.usage_limit,
            per_customer_limit=payload.per_customer_limit,
            is_active=payload.is_active,
            first_order_only=payload.first_order_only,
            exclude_discounted=payload.exclude_discounted,
            free_shipping=payload.free_shipping,
        )
        self._set_targets(discount, payload)
        self.session.add(discount)
        await self.session.commit()
        return await self.get_or_404(discount.id)

    async def update(self, discount_id: uuid.UUID, payload: DiscountUpdate) -> Discount:
        discount = await self.get_or_404(discount_id)
        provided = payload.model_fields_set

        if payload.code is not None or "code" in provided:
            code = self._normalise_code(payload.code)
            if code is not None and code.lower() != (discount.code or "").lower():
                await self._assert_code_free(code, exclude_id=discount.id)
            discount.code = code

        scope = payload.scope if payload.scope is not None else discount.scope
        type_ = payload.type if payload.type is not None else discount.type
        value = payload.value if payload.value is not None else discount.value
        self._assert_value(scope, type_, value)
        discount.scope = scope
        discount.type = type_
        discount.value = money(value)

        starts_at = payload.starts_at if "starts_at" in provided else discount.starts_at
        expires_at = payload.expires_at if "expires_at" in provided else discount.expires_at
        self._assert_window(starts_at, expires_at)

        if payload.name is not None:
            discount.name = payload.name.strip()
        if payload.min_order_amount is not None:
            discount.min_order_amount = money(payload.min_order_amount)
        if "max_discount_amount" in provided:
            discount.max_discount_amount = (
                money(payload.max_discount_amount)
                if payload.max_discount_amount is not None
                else None
            )
        if "starts_at" in provided:
            discount.starts_at = starts_at
        if "expires_at" in provided:
            discount.expires_at = expires_at
        if "usage_limit" in provided:
            discount.usage_limit = payload.usage_limit
        if "per_customer_limit" in provided:
            discount.per_customer_limit = payload.per_customer_limit
        if payload.is_active is not None:
            discount.is_active = payload.is_active
        if payload.first_order_only is not None:
            discount.first_order_only = payload.first_order_only
        if payload.exclude_discounted is not None:
            discount.exclude_discounted = payload.exclude_discounted
        if payload.free_shipping is not None:
            discount.free_shipping = payload.free_shipping

        if (
            payload.product_ids is not None
            or payload.category_ids is not None
            or payload.brand_ids is not None
        ):
            await self._assert_targets(
                payload.product_ids or [], payload.category_ids or [], payload.brand_ids or []
            )
            discount.products = []
            discount.categories = []
            discount.brands = []
            self._set_targets(discount, payload)

        await self.session.commit()
        return await self.get_or_404(discount.id)

    async def delete(self, discount_id: uuid.UUID) -> None:
        discount = await self.get_or_404(discount_id)
        discount.is_active = False
        discount.deleted_at = datetime.now(UTC)
        await self.session.commit()

    # --- Pricing -----------------------------------------------------------
    async def price(
        self,
        rows: Sequence[DiscountLineInput],
        *,
        customer_id: uuid.UUID | None,
        coupon_code: str | None,
        order_discount: Decimal,
        business: Business | None = None,
    ) -> Pricing:
        """Value a basket: automatic promos, manual discounts, then a coupon.

        ``business`` supplies the tax settings, so the tax and the amount payable
        are part of the same calculation the sale will use. Omitted (``None``),
        tax is zero — the sale always passes it.
        """
        lines = await self._resolve_lines(rows)
        subtotal = money(sum((line.subtotal for line in lines), ZERO))

        code = self._normalise_code(coupon_code)
        coupon = (
            await self.resolve_coupon(code, subtotal=subtotal, customer_id=customer_id)
            if code
            else None
        )

        now = datetime.now(UTC)
        candidates = sorted(
            await self.discounts.list_priced_candidates(),
            key=lambda d: (d.created_at, str(d.id)),
        )

        applied: list[AppliedDiscount] = []
        auto_by_line: dict[uuid.UUID, Decimal] = {line.product_id: ZERO for line in lines}
        promo_totals: dict[uuid.UUID, Decimal] = {}
        promo_names: dict[uuid.UUID, Discount] = {}

        # 1. Automatic product promotions, per line, capped at the line subtotal.
        for discount in candidates:
            if discount.is_coupon or discount.scope != "product":
                continue
            if not self._in_window(discount, now):
                continue
            if subtotal < discount.min_order_amount:
                continue
            for line in lines:
                if not self._targets(discount, line):
                    continue
                if discount.exclude_discounted and (
                    line.has_discount_price or auto_by_line[line.product_id] > 0
                ):
                    continue
                remaining = line.subtotal - auto_by_line[line.product_id]
                amount = min(self._line_amount(discount, line), remaining)
                if amount <= 0:
                    continue
                auto_by_line[line.product_id] += amount
                promo_totals[discount.id] = promo_totals.get(discount.id, ZERO) + amount
                promo_names[discount.id] = discount

        for discount_id, amount in promo_totals.items():
            record = promo_names[discount_id]
            applied.append(
                AppliedDiscount(discount_id=record.id, code=None, name=record.name, amount=amount)
            )

        # 2. Manual line discounts ride on top, still capped at the line.
        priced: list[PricedLine] = []
        line_totals: dict[uuid.UUID, Decimal] = {}
        line_discounts = ZERO
        for line in lines:
            auto = auto_by_line[line.product_id]
            manual = min(line.manual_discount, line.subtotal - auto)
            total = money(auto + manual)
            line_discounts += total
            line_total = money(line.subtotal - total)
            line_totals[line.product_id] = line_total
            priced.append(
                PricedLine(
                    product_id=line.product_id,
                    product_name=line.product_name,
                    sku=line.sku,
                    unit=line.unit,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    cost_price=line.cost_price,
                    subtotal=line.subtotal,
                    manual_discount=money(manual),
                    automatic_discount=money(auto),
                    discount=total,
                    line_total=line_total,
                )
            )
        line_discounts = money(line_discounts)
        running = money(subtotal - line_discounts)

        # 3. Automatic cart promotions.
        cart_discount = ZERO
        for discount in candidates:
            if discount.is_coupon or discount.scope != "cart":
                continue
            if not self._in_window(discount, now):
                continue
            if subtotal < discount.min_order_amount:
                continue
            amount = min(self._order_amount(discount, running), running)
            if amount <= 0:
                continue
            cart_discount += amount
            running = money(running - amount)
            applied.append(
                AppliedDiscount(
                    discount_id=discount.id, code=None, name=discount.name, amount=amount
                )
            )
        cart_discount = money(cart_discount)

        # 4. The coupon, off its eligible base.
        coupon_discount = ZERO
        if coupon is not None:
            base = self._coupon_base(coupon, lines, line_totals, running)
            if base <= 0:
                raise UnprocessableError(
                    "This coupon does not apply to anything in the basket.",
                    code="coupon_not_applicable",
                )
            amount = min(self._order_amount(coupon, base), running)
            if amount <= 0:
                raise UnprocessableError(
                    "This coupon does not apply to this basket.", code="coupon_not_applicable"
                )
            coupon_discount = money(amount)
            running = money(running - amount)
            applied.append(
                AppliedDiscount(
                    discount_id=coupon.id, code=coupon.code, name=coupon.name, amount=amount
                )
            )

        # 5. The cashier's manual order discount, capped at what remains.
        manual_order = money(order_discount)
        if money(line_discounts + manual_order) > subtotal:
            raise UnprocessableError(
                "The discount cannot exceed the subtotal.",
                code="discount_exceeds_subtotal",
                details=[{"field": "order_discount", "message": "Greater than the subtotal."}],
            )
        manual_order = min(manual_order, running)
        running = money(running - manual_order)

        total_discount = money(line_discounts + cart_discount + coupon_discount + manual_order)
        net = running
        tax = tax_for(net, business)
        return Pricing(
            lines=priced,
            subtotal=subtotal,
            line_discounts=line_discounts,
            cart_discount=cart_discount,
            coupon_discount=coupon_discount,
            order_discount=money(manual_order),
            total_discount=total_discount,
            net=net,
            tax=tax,
            total=total_for(net, tax, business),
            coupon_code=coupon.code if coupon else None,
            applied=applied,
        )

    async def preview(
        self,
        rows: Sequence[DiscountLineInput],
        *,
        customer_id: uuid.UUID | None,
        coupon_code: str | None,
        order_discount: Decimal,
    ) -> PriceBreakdown:
        """Price a basket for the till: discounts plus the tax and amount due.

        The same engine the sale runs, so the figure shown here is the figure the
        sale is recorded at.
        """
        pricing = await self.price(
            rows,
            customer_id=customer_id,
            coupon_code=coupon_code,
            order_discount=order_discount,
            business=await self.business.get_default(),
        )
        return pricing.breakdown()

    async def resolve_coupon(
        self, code: str, *, subtotal: Decimal, customer_id: uuid.UUID | None
    ) -> Discount:
        """Every coupon rule, checked server-side, in the order a cashier hits them."""
        discount = await self.discounts.get_by_code(code)
        if discount is None:
            raise UnprocessableError("That coupon code is not recognised.", code="coupon_not_found")
        if not discount.is_active:
            raise UnprocessableError("That coupon is not active.", code="coupon_inactive")

        now = datetime.now(UTC)
        if discount.starts_at is not None and now < discount.starts_at:
            raise UnprocessableError("That coupon is not valid yet.", code="coupon_not_started")
        if discount.expires_at is not None and now > discount.expires_at:
            raise UnprocessableError("That coupon has expired.", code="coupon_expired")
        if subtotal < discount.min_order_amount:
            raise UnprocessableError(
                f"This coupon needs a minimum spend of {discount.min_order_amount}.",
                code="coupon_min_order",
                details=[{"field": "coupon_code", "message": "Basket is below the minimum."}],
            )
        if (
            discount.usage_limit is not None
            and await self.redemptions.count_for_discount(discount.id) >= discount.usage_limit
        ):
            raise UnprocessableError(
                "That coupon has reached its usage limit.", code="coupon_usage_limit"
            )
        if (discount.per_customer_limit is not None or discount.first_order_only) and (
            customer_id is None
        ):
            raise UnprocessableError(
                "This coupon needs a customer to be attached to the sale.",
                code="coupon_requires_customer",
                details=[{"field": "customer_id", "message": "Required for this coupon."}],
            )
        if discount.per_customer_limit is not None:
            used = await self.redemptions.count_for_customer(discount.id, customer_id)  # type: ignore[arg-type]
            if used >= discount.per_customer_limit:
                raise UnprocessableError(
                    "This customer has already used that coupon.",
                    code="coupon_customer_limit",
                )
        if discount.first_order_only:
            orders, _ = await self.sales.totals_for_customer(customer_id)  # type: ignore[arg-type]
            if orders > 0:
                raise UnprocessableError(
                    "That coupon is only valid on a customer's first order.",
                    code="coupon_first_order_only",
                )
        return discount

    def redemption_rows(
        self, pricing: Pricing, *, sale_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> list[DiscountRedemption]:
        """The applied discounts, ready to persist with the sale."""
        return [
            DiscountRedemption(
                discount_id=entry.discount_id,
                sale_id=sale_id,
                customer_id=customer_id,
                code=entry.code,
                name=entry.name,
                amount=entry.amount,
            )
            for entry in pricing.applied
            if entry.amount > 0
        ]

    # --- Internals ---------------------------------------------------------
    async def _resolve_lines(self, rows: Sequence[DiscountLineInput]) -> list[_Line]:
        seen: set[uuid.UUID] = set()
        lines: list[_Line] = []

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

            unit_price = money(
                product.discount_price
                if product.discount_price is not None
                else product.selling_price
            )
            line_subtotal = money(row.quantity * unit_price)
            manual = money(row.discount)
            if manual > line_subtotal:
                raise UnprocessableError(
                    f"The discount on {product.name} is more than the line total.",
                    code="discount_exceeds_line",
                    details=[{"field": "items", "message": "Line discount too large."}],
                )

            lines.append(
                _Line(
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    unit=product.unit,
                    quantity=row.quantity,
                    unit_price=unit_price,
                    cost_price=money(product.purchase_price),
                    subtotal=line_subtotal,
                    manual_discount=manual,
                    category_id=product.category_id,
                    brand_id=product.brand_id,
                    has_discount_price=product.discount_price is not None,
                )
            )
        return lines

    @staticmethod
    def _in_window(discount: Discount, now: datetime) -> bool:
        if discount.starts_at is not None and now < discount.starts_at:
            return False
        return not (discount.expires_at is not None and now > discount.expires_at)

    @staticmethod
    def _targets(discount: Discount, line: _Line) -> bool:
        products = discount.product_ids
        categories = discount.category_ids
        brands = discount.brand_ids
        if not (products or categories or brands):
            return True  # an untargeted product discount covers everything
        return (
            line.product_id in products
            or (line.category_id is not None and line.category_id in categories)
            or (line.brand_id is not None and line.brand_id in brands)
        )

    @staticmethod
    def _line_amount(discount: Discount, line: _Line) -> Decimal:
        if discount.type == "percentage":
            return money(line.subtotal * discount.value / HUNDRED)
        return money(discount.value * line.quantity)

    @staticmethod
    def _order_amount(discount: Discount, base: Decimal) -> Decimal:
        amount = (
            money(base * discount.value / HUNDRED)
            if discount.type == "percentage"
            else money(discount.value)
        )
        if discount.max_discount_amount is not None:
            amount = min(amount, money(discount.max_discount_amount))
        return max(amount, ZERO)

    @staticmethod
    def _coupon_base(
        coupon: Discount,
        lines: list[_Line],
        line_totals: dict[uuid.UUID, Decimal],
        running: Decimal,
    ) -> Decimal:
        """What a coupon is computed against: the whole basket, or its eligible lines.

        Uses the original lines so category/brand targeting is honoured.
        """
        if coupon.scope == "cart":
            return running
        eligible = [line for line in lines if DiscountService._targets(coupon, line)]
        return money(sum((line_totals[line.product_id] for line in eligible), ZERO))

    # --- Validation helpers ------------------------------------------------
    @staticmethod
    def _normalise_code(code: str | None) -> str | None:
        if code is None:
            return None
        cleaned = code.strip().upper()
        return cleaned or None

    async def _assert_code_free(self, code: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if await self.discounts.code_exists(code, exclude_id=exclude_id):
            raise ConflictError(
                "A discount with that code already exists.",
                code="discount_code_taken",
                details=[{"field": "code", "message": "Already in use."}],
            )

    @staticmethod
    def _assert_value(scope: str, type_: str, value: Decimal) -> None:
        if type_ == "percentage" and money(value) > HUNDRED:
            raise UnprocessableError(
                "A percentage discount cannot exceed 100.",
                code="discount_value_invalid",
                details=[{"field": "value", "message": "Must be 100 or less."}],
            )

    @staticmethod
    def _assert_window(starts_at: datetime | None, expires_at: datetime | None) -> None:
        if starts_at is not None and expires_at is not None and expires_at < starts_at:
            raise UnprocessableError(
                "The expiry date cannot be before the start date.",
                code="discount_window_invalid",
                details=[{"field": "expires_at", "message": "Before the start date."}],
            )

    async def _assert_targets(
        self,
        product_ids: Sequence[uuid.UUID],
        category_ids: Sequence[uuid.UUID],
        brand_ids: Sequence[uuid.UUID],
    ) -> None:
        for product_id in product_ids:
            product = await self.products.get(product_id)
            if product is None or product.is_deleted:
                raise UnprocessableError(
                    "A targeted product does not exist.",
                    code="unknown_target",
                    details=[{"field": "product_ids", "message": str(product_id)}],
                )
        for category_id in category_ids:
            category = await self.categories.get(category_id)
            if category is None or category.is_deleted:
                raise UnprocessableError(
                    "A targeted category does not exist.",
                    code="unknown_target",
                    details=[{"field": "category_ids", "message": str(category_id)}],
                )
        for brand_id in brand_ids:
            brand = await self.brands.get(brand_id)
            if brand is None or brand.is_deleted:
                raise UnprocessableError(
                    "A targeted brand does not exist.",
                    code="unknown_target",
                    details=[{"field": "brand_ids", "message": str(brand_id)}],
                )

    @staticmethod
    def _set_targets(discount: Discount, payload: DiscountCreate | DiscountUpdate) -> None:
        from app.models.discount import DiscountBrand, DiscountCategory, DiscountProduct

        for product_id in payload.product_ids or []:
            discount.products.append(DiscountProduct(product_id=product_id))
        for category_id in payload.category_ids or []:
            discount.categories.append(DiscountCategory(category_id=category_id))
        for brand_id in payload.brand_ids or []:
            discount.brands.append(DiscountBrand(brand_id=brand_id))
