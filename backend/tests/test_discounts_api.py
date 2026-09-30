"""MODULE 17 — discounts and coupons: the server prices, the client only previews."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
CATEGORIES = "/api/v1/categories"
CUSTOMERS = "/api/v1/customers"
SALES = "/api/v1/sales"
DISCOUNTS = "/api/v1/discounts"
REGISTER_SESSIONS = "/api/v1/register-sessions"


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------
async def _product(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "BEAN-1",
        "minimum_stock": "0",
        "opening_stock": "20",
        "purchase_price": "1.00",
        "selling_price": "2.00",
    }
    payload.update(overrides)
    response = await client.post(PRODUCTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _category(client: AsyncClient, headers: dict[str, str], name: str) -> dict[str, Any]:
    response = await client.post(CATEGORIES, headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def _customer(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Jane Doe"}
    payload.update(overrides)
    response = await client.post(CUSTOMERS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _discount(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Promo",
        "scope": "cart",
        "type": "percentage",
        "value": "10",
    }
    payload.update(overrides)
    response = await client.post(DISCOUNTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _ensure_session(client: AsyncClient, headers: dict[str, str], seeded: Any) -> None:
    register_id = str(seeded.register.id)
    current = await client.get(
        f"{REGISTER_SESSIONS}/current", headers=headers, params={"register_id": register_id}
    )
    if current.status_code == 200 and current.json() is None:
        opened = await client.post(
            REGISTER_SESSIONS,
            headers=headers,
            json={"register_id": register_id, "opening_cash": "0"},
        )
        assert opened.status_code == 201, opened.text


def _cash(payment_methods: dict[str, Any], amount: str) -> dict[str, Any]:
    return {"payment_method_id": str(payment_methods["CASH"].id), "amount": amount}


async def _sell(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: Any,
    items: list[dict[str, Any]],
    *,
    pay: str,
    **overrides: Any,
) -> Any:
    await _ensure_session(client, headers, seeded)
    return await client.post(
        SALES,
        headers=headers,
        json={
            "branch_id": str(seeded.branch.id),
            "register_id": str(seeded.register.id),
            "items": items,
            "payments": [_cash(seeded.payment_methods, pay)],
            **overrides,
        },
    )


async def _preview(
    client: AsyncClient, headers: dict[str, str], items: list[dict[str, Any]], **overrides: Any
) -> Any:
    return await client.post(
        DISCOUNTS + "/validate", headers=headers, json={"items": items, **overrides}
    )


# ---------------------------------------------------------------------------
# Management
# ---------------------------------------------------------------------------
async def test_discounts_can_be_created_listed_and_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await _discount(client, auth_headers, name="Ten off", code="ten", value="10")
    assert created["code"] == "TEN"  # codes are normalised

    listing = await client.get(DISCOUNTS, headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    coupons = await client.get(DISCOUNTS, headers=auth_headers, params={"coupons_only": "true"})
    assert coupons.json()["total"] == 1

    duplicate = await client.post(
        DISCOUNTS, headers=auth_headers, json={"name": "Other", "code": "TEN"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "discount_code_taken"

    assert (
        await client.delete(f"{DISCOUNTS}/{created['id']}", headers=auth_headers)
    ).status_code == 204
    assert (await client.get(DISCOUNTS, headers=auth_headers)).json()["total"] == 0


async def test_a_percentage_over_100_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        DISCOUNTS,
        headers=auth_headers,
        json={"name": "Too much", "type": "percentage", "value": "150"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "discount_value_invalid"


async def test_the_automatic_filter_excludes_coupons(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _discount(client, auth_headers, name="Always on")
    await _discount(client, auth_headers, name="Coded", code="CODED")

    automatic = await client.get(DISCOUNTS, headers=auth_headers, params={"coupons_only": "false"})

    assert automatic.status_code == 200, automatic.text
    assert automatic.json()["total"] == 1
    assert automatic.json()["items"][0]["name"] == "Always on"


# ---------------------------------------------------------------------------
# Automatic promotions
# ---------------------------------------------------------------------------
async def test_a_product_promotion_discounts_the_line(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    await _discount(
        client, auth_headers, name="Bean sale", scope="product", type="percentage", value="10"
    )

    created = await _sell(
        client,
        auth_headers,
        seeded,
        [{"product_id": product["id"], "quantity": "3"}],
        pay="5.40",
    )

    assert created.status_code == 201, created.text
    sale = created.json()
    assert sale["subtotal"] == "6.00"
    assert sale["discount"] == "0.60"
    assert sale["total"] == "5.40"
    assert sale["items"][0]["discount"] == "0.60"
    assert [row["name"] for row in sale["discounts"]] == ["Bean sale"]


async def test_a_cart_promotion_discounts_the_whole_basket(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    await _discount(client, auth_headers, name="10% off", scope="cart", value="10")

    created = await _sell(
        client, auth_headers, seeded, [{"product_id": product["id"], "quantity": "3"}], pay="5.40"
    )

    assert created.json()["discount"] == "0.60"


async def test_a_manual_line_discount_stacks_with_a_promotion(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    await _discount(client, auth_headers, name="10% off", scope="cart", value="10")

    created = await _sell(
        client,
        auth_headers,
        seeded,
        [{"product_id": product["id"], "quantity": "3", "discount": "1.00"}],
        pay="4.50",
    )

    assert created.status_code == 201, created.text
    # 1.00 manual + 10% of the 5.00 that remains = 1.50.
    assert created.json()["discount"] == "1.50"


async def test_stacking_is_capped_at_the_line(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """A 100% product promo plus a manual discount can never exceed the line."""
    product = await _product(client, auth_headers)
    await _discount(
        client, auth_headers, name="Free", scope="product", type="percentage", value="100"
    )

    preview = await _preview(
        client,
        auth_headers,
        [{"product_id": product["id"], "quantity": "2", "discount": "3.00"}],
    )

    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["subtotal"] == "4.00"
    # The 100% promo takes the whole line; the manual discount gets nothing.
    assert body["total_discount"] == "4.00"
    assert body["net"] == "0.00"


async def test_exclude_discounted_skips_a_product_already_on_sale(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """A promotion can keep its hands off lines that already carry a sale price."""
    on_sale = await _product(
        client, auth_headers, name="Clearance", sku="CLEAR-1", discount_price="1.50"
    )
    await _discount(
        client,
        auth_headers,
        name="10% off",
        scope="product",
        type="percentage",
        value="10",
        exclude_discounted=True,
    )

    preview = await _preview(
        client, auth_headers, [{"product_id": on_sale["id"], "quantity": "2"}]
    )

    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["subtotal"] == "3.00"  # 2 x the 1.50 sale price
    assert body["total_discount"] == "0.00"
    assert body["net"] == "3.00"


async def test_an_automatic_promotion_respects_its_minimum_order(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    product = await _product(client, auth_headers)
    await _discount(
        client, auth_headers, name="Big spender", scope="cart", value="10", min_order_amount="50"
    )

    preview = await _preview(
        client, auth_headers, [{"product_id": product["id"], "quantity": "3"}]
    )

    assert preview.status_code == 200, preview.text
    assert preview.json()["total_discount"] == "0.00"


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
async def test_a_coupon_reduces_the_total_and_is_recorded(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    await _discount(
        client, auth_headers, name="Save one", code="SAVE1", scope="cart", type="fixed", value="1"
    )

    created = await _sell(
        client,
        auth_headers,
        seeded,
        [{"product_id": product["id"], "quantity": "3"}],
        pay="5.00",
        coupon_code="save1",
    )

    assert created.status_code == 201, created.text
    sale = created.json()
    assert sale["discount"] == "1.00"
    assert sale["total"] == "5.00"
    assert sale["discounts"] == [{"code": "SAVE1", "name": "Save one", "amount": "1.00"}]


async def test_the_list_reports_how_often_each_discount_was_used(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    await _discount(
        client, auth_headers, name="Save one", code="SAVE1", scope="cart", type="fixed", value="1"
    )

    sale = await _sell(
        client,
        auth_headers,
        seeded,
        [{"product_id": product["id"], "quantity": "1"}],
        pay="1.00",
        coupon_code="SAVE1",
    )
    assert sale.status_code == 201, sale.text

    listing = await client.get(DISCOUNTS, headers=auth_headers)
    assert listing.json()["items"][0]["redeemed_count"] == 1


async def test_a_category_scoped_coupon_only_counts_its_own_lines(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    drinks = await _category(client, auth_headers, "Drinks")
    in_category = await _product(
        client, auth_headers, name="Cola", sku="COLA", category_id=drinks["id"]
    )
    other = await _product(client, auth_headers, name="Bread", sku="BREAD")

    await _discount(
        client,
        auth_headers,
        name="Half off drinks",
        code="DRINKS50",
        scope="product",
        type="percentage",
        value="50",
        category_ids=[drinks["id"]],
    )

    preview = await _preview(
        client,
        auth_headers,
        [
            {"product_id": in_category["id"], "quantity": "2"},  # 4.00
            {"product_id": other["id"], "quantity": "1"},  # 3.00
        ],
        coupon_code="DRINKS50",
    )

    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["subtotal"] == "6.00"  # drinks 4.00 + bread 2.00
    assert body["coupon_discount"] == "2.00"  # half of the 4.00 drinks line
    assert body["net"] == "4.00"


async def test_a_coupon_is_capped_by_max_discount(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    product = await _product(client, auth_headers)
    await _discount(
        client,
        auth_headers,
        name="Huge but capped",
        code="CAP5",
        scope="cart",
        type="fixed",
        value="999",
        max_discount_amount="5",
    )

    preview = await _preview(
        client,
        auth_headers,
        [{"product_id": product["id"], "quantity": "3"}],  # 6.00
        coupon_code="CAP5",
    )

    assert preview.json()["coupon_discount"] == "5.00"


async def test_coupon_validation_covers_every_rule(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    item = [{"product_id": product["id"], "quantity": "1"}]  # 2.00

    async def code_for(name: str, **overrides: Any) -> str:
        payload: dict[str, Any] = {"name": name, "scope": "cart", "type": "fixed", "value": "1"}
        payload.update(overrides)
        created = await _discount(client, auth_headers, **payload)
        return created["code"]

    async def expect(code: str, expected: str, **extra: Any) -> None:
        response = await _preview(client, auth_headers, item, coupon_code=code, **extra)
        assert response.status_code == 422, response.text
        assert response.json()["error"]["code"] == expected, response.text

    await expect("NOPE", "coupon_not_found")

    inactive = await code_for("Inactive", code="OFF1", is_active=False)
    await expect(inactive, "coupon_inactive")

    expired = await code_for("Expired", code="OLD", expires_at="2020-01-01T00:00:00Z")
    await expect(expired, "coupon_expired")

    future = await code_for("Future", code="SOON", starts_at="2999-01-01T00:00:00Z")
    await expect(future, "coupon_not_started")

    big_min = await code_for("Big min", code="MIN100", min_order_amount="100")
    await expect(big_min, "coupon_min_order")

    other = await _product(client, auth_headers, name="Other", sku="OTHER-1")
    not_applicable = await code_for(
        "Wrong product", code="ONLYOTHER", scope="product", product_ids=[other["id"]]
    )
    await expect(not_applicable, "coupon_not_applicable")

    # Usage limit: the first sale consumes the coupon's single use.
    once = await code_for("Once", code="ONCE", usage_limit=1)
    first = await _sell(
        client, auth_headers, seeded, item, pay="1.00", coupon_code=once
    )
    assert first.status_code == 201, first.text
    await expect(once, "coupon_usage_limit")

    # Per-customer limit needs a customer, and is counted per customer.
    customer = await _customer(client, auth_headers, name="Repeat")
    per_customer = await code_for("Per customer", code="PERCUST", per_customer_limit=1)
    first_for = await _sell(
        client,
        auth_headers,
        seeded,
        item,
        pay="1.00",
        coupon_code=per_customer,
        customer_id=customer["id"],
    )
    assert first_for.status_code == 201, first_for.text
    response = await _preview(
        client, auth_headers, item, coupon_code=per_customer, customer_id=customer["id"]
    )
    assert response.json()["error"]["code"] == "coupon_customer_limit"

    # First-order-only: the customer above already has an order.
    first_only = await code_for("First order", code="FIRST", first_order_only=True)
    response = await _preview(
        client, auth_headers, item, coupon_code=first_only, customer_id=customer["id"]
    )
    assert response.json()["error"]["code"] == "coupon_first_order_only"

    # …and it needs a customer at all.
    await expect(first_only, "coupon_requires_customer")


# ---------------------------------------------------------------------------
# Preview never persists
# ---------------------------------------------------------------------------
async def test_the_preview_does_not_create_a_sale(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    product = await _product(client, auth_headers)

    response = await _preview(
        client, auth_headers, [{"product_id": product["id"], "quantity": "2"}]
    )

    assert response.status_code == 200, response.text
    assert response.json()["subtotal"] == "4.00"
    assert (await client.get(SALES, headers=auth_headers)).json()["total"] == 0


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_a_cashier_can_preview_but_not_manage_discounts(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    product = await _product(client, auth_headers)

    forbidden = await client.post(
        DISCOUNTS, headers=cashier_headers, json={"name": "Nope", "value": "5"}
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "insufficient_permissions"

    allowed = await _preview(
        client, cashier_headers, [{"product_id": product["id"], "quantity": "1"}]
    )
    assert allowed.status_code == 200, allowed.text
