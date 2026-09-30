"""MODULE 18 — reporting: the server aggregates, the client only displays."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy import update

from app.models.sale import Sale

PRODUCTS = "/api/v1/products"
CATEGORIES = "/api/v1/categories"
CUSTOMERS = "/api/v1/customers"
SUPPLIERS = "/api/v1/suppliers"
SALES = "/api/v1/sales"
PURCHASES = "/api/v1/purchases"
EXPENSES = "/api/v1/expenses"
EXPENSE_CATEGORIES = "/api/v1/expense-categories"
INVENTORY = "/api/v1/inventory"
REGISTER_SESSIONS = "/api/v1/register-sessions"
REPORTS = "/api/v1/reports"


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


async def _supplier(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Acme Supplies"}
    payload.update(overrides)
    response = await client.post(SUPPLIERS, headers=headers, json=payload)
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
) -> dict[str, Any]:
    await _ensure_session(client, headers, seeded)
    response = await client.post(
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
    assert response.status_code == 201, response.text
    return response.json()


async def _receive_purchase(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: Any,
    supplier_id: str,
    product_id: str,
    *,
    quantity: str,
    unit_price: str,
    paid: str = "0",
) -> dict[str, Any]:
    created = await client.post(
        PURCHASES,
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "branch_id": str(seeded.branch.id),
            "purchase_date": date.today().isoformat(),
            "paid": paid,
            "items": [{"product_id": product_id, "quantity": quantity, "unit_price": unit_price}],
        },
    )
    assert created.status_code == 201, created.text
    received = await client.post(
        f"{PURCHASES}/{created.json()['id']}/receive", headers=headers
    )
    assert received.status_code == 200, received.text
    return received.json()


async def _expense(
    client: AsyncClient, headers: dict[str, str], seeded: Any, amount: str
) -> dict[str, Any]:
    categories = await client.get(f"{EXPENSE_CATEGORIES}/options", headers=headers)
    assert categories.status_code == 200, categories.text
    response = await client.post(
        EXPENSES,
        headers=headers,
        json={
            "branch_id": str(seeded.branch.id),
            "category_id": categories.json()[0]["id"],
            "payment_method_id": str(seeded.payment_methods["CARD"].id),
            "amount": amount,
            "spent_at": date.today().isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _report(
    client: AsyncClient, headers: dict[str, str], name: str, **params: Any
) -> dict[str, Any]:
    response = await client.get(f"{REPORTS}/{name}", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------
async def test_sales_report_totals_and_breakdowns(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    drinks = await _category(client, auth_headers, "Drinks")
    product = await _product(client, auth_headers, category_id=drinks["id"])
    await _sell(
        client, auth_headers, seeded, [{"product_id": product["id"], "quantity": "3"}], pay="6.00"
    )

    report = await _report(client, auth_headers, "sales", preset="today")

    summary = report["summary"]
    assert Decimal(summary["total_sales"]) == Decimal("6.00")
    assert summary["order_count"] == 1
    assert Decimal(summary["average_order_value"]) == Decimal("6.00")
    assert Decimal(summary["items_sold"]) == Decimal("3")
    assert Decimal(summary["refunded_amount"]) == Decimal("0.00")

    # The captured cost (1.00 x 3) drives gross profit.
    row = report["by_product"][0]
    assert row["sku"] == "BEAN-1"
    assert Decimal(row["net"]) == Decimal("6.00")
    assert Decimal(row["cost"]) == Decimal("3.00")
    assert Decimal(row["profit"]) == Decimal("3.00")

    assert report["by_category"][0]["name"] == "Drinks"
    assert report["by_cashier"][0]["name"] == "Test Administrator"
    assert report["by_branch"][0]["name"] == seeded.branch.name
    method = report["by_payment_method"][0]
    assert method["kind"] == "cash"
    assert Decimal(method["amount"]) == Decimal("6.00")
    assert report["daily"][0]["orders"] == 1


async def test_voided_sales_are_excluded(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any, db_session: Any
) -> None:
    product = await _product(client, auth_headers)
    sale = await _sell(
        client, auth_headers, seeded, [{"product_id": product["id"], "quantity": "1"}], pay="2.00"
    )

    await db_session.execute(
        update(Sale).where(Sale.id == sale["id"]).values(status="voided")
    )
    await db_session.commit()

    report = await _report(client, auth_headers, "sales", preset="today")
    assert report["summary"]["order_count"] == 0
    assert Decimal(report["summary"]["total_sales"]) == Decimal("0.00")


async def test_revenue_is_net_of_returns(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    sale = await _sell(
        client, auth_headers, seeded, [{"product_id": product["id"], "quantity": "3"}], pay="6.00"
    )

    returned = await client.post(
        f"{SALES}/{sale['id']}/returns",
        headers=auth_headers,
        json={
            "items": [{"sale_item_id": sale["items"][0]["id"], "quantity": "1"}],
            "payment_method_id": str(seeded.payment_methods["CASH"].id),
        },
    )
    assert returned.status_code == 201, returned.text

    report = await _report(client, auth_headers, "sales", preset="today")
    # 6.00 charged, 2.00 refunded for the one unit that came back.
    assert Decimal(report["summary"]["total_sales"]) == Decimal("4.00")
    assert Decimal(report["summary"]["refunded_amount"]) == Decimal("2.00")
    assert report["summary"]["returns_count"] == 1


# ---------------------------------------------------------------------------
# Purchases
# ---------------------------------------------------------------------------
async def test_purchases_report(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    supplier = await _supplier(client, auth_headers)
    product = await _product(client, auth_headers)
    await _receive_purchase(
        client,
        auth_headers,
        seeded,
        supplier["id"],
        product["id"],
        quantity="5",
        unit_price="1.00",
        paid="2.00",
    )

    report = await _report(client, auth_headers, "purchases", preset="today")

    summary = report["summary"]
    assert Decimal(summary["total_purchases"]) == Decimal("5.00")
    assert summary["purchase_count"] == 1
    assert Decimal(summary["paid"]) == Decimal("2.00")
    assert Decimal(summary["outstanding_due"]) == Decimal("3.00")

    row = report["by_supplier"][0]
    assert row["name"] == "Acme Supplies"
    assert Decimal(row["due"]) == Decimal("3.00")


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
async def test_inventory_report_values_stock_and_movements(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="20")  # 20 @ cost 1.00
    moved = await client.post(
        f"{INVENTORY}/movements",
        headers=auth_headers,
        json={
            "product_id": product["id"],
            "branch_id": str(seeded.branch.id),
            "movement_type": "adjustment",
            "quantity": "5",
        },
    )
    assert moved.status_code == 201, moved.text

    report = await _report(client, auth_headers, "inventory", preset="today")

    totals = report["totals"]
    assert Decimal(totals["total_quantity"]) == Decimal("25")
    assert Decimal(totals["stock_value_cost"]) == Decimal("25.00")
    assert Decimal(totals["stock_value_retail"]) == Decimal("50.00")
    assert totals["product_count"] == 1

    by_type = {row["movement_type"]: row for row in report["movements"]}
    assert by_type["adjustment"]["count"] == 1
    assert Decimal(by_type["adjustment"]["net_quantity"]) == Decimal("5")

    assert report["adjustments"]["count"] == 1
    assert Decimal(report["adjustments"]["net_quantity"]) == Decimal("5")


async def test_inventory_report_flags_low_and_out_of_stock(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _product(
        client,
        auth_headers,
        name="Low",
        sku="LOW-1",
        minimum_stock="10",
        opening_stock="4",
    )
    await _product(
        client,
        auth_headers,
        name="Gone",
        sku="GONE-1",
        minimum_stock="1",
        opening_stock="0",
    )

    report = await _report(client, auth_headers, "inventory", preset="today")

    assert [row["sku"] for row in report["low_stock"]] == ["LOW-1"]
    assert [row["sku"] for row in report["out_of_stock"]] == ["GONE-1"]
    assert report["totals"]["low_stock"] == 1
    assert report["totals"]["out_of_stock"] == 1


# ---------------------------------------------------------------------------
# Financial
# ---------------------------------------------------------------------------
async def test_financial_report_ties_out(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    supplier = await _supplier(client, auth_headers)
    product = await _product(client, auth_headers)
    await _receive_purchase(
        client,
        auth_headers,
        seeded,
        supplier["id"],
        product["id"],
        quantity="10",
        unit_price="1.00",
        paid="7.00",
    )
    await _sell(
        client, auth_headers, seeded, [{"product_id": product["id"], "quantity": "3"}], pay="6.00"
    )
    await _expense(client, auth_headers, seeded, amount="1.50")
    await _customer(client, auth_headers, name="Owing", opening_balance="10.00")

    report = await _report(client, auth_headers, "financial", preset="today")

    assert Decimal(report["revenue"]) == Decimal("6.00")
    assert Decimal(report["cost"]) == Decimal("3.00")
    assert Decimal(report["gross_profit"]) == Decimal("3.00")
    assert Decimal(report["gross_margin"]) == Decimal("50.00")
    assert Decimal(report["expenses"]) == Decimal("1.50")
    assert Decimal(report["net_profit"]) == Decimal("1.50")
    assert Decimal(report["customer_due"]) == Decimal("10.00")
    assert Decimal(report["supplier_due"]) == Decimal("3.00")


# ---------------------------------------------------------------------------
# Date ranges
# ---------------------------------------------------------------------------
async def test_presets_and_custom_ranges_resolve(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    today = date.today()

    month = await _report(client, auth_headers, "sales", preset="this_month")
    assert month["range"]["preset"] == "this_month"
    assert month["range"]["start"] == today.replace(day=1).isoformat()
    assert month["range"]["end"] == today.isoformat()

    yesterday = await _report(client, auth_headers, "sales", preset="yesterday")
    expected = (today - timedelta(days=1)).isoformat()
    assert yesterday["range"]["start"] == expected
    assert yesterday["range"]["end"] == expected

    custom = await _report(
        client,
        auth_headers,
        "sales",
        preset="custom",
        date_from="2026-01-01",
        date_to="2026-01-31",
    )
    assert custom["range"]["preset"] == "custom"
    assert custom["range"]["start"] == "2026-01-01"
    assert custom["range"]["end"] == "2026-01-31"


async def test_a_custom_range_needs_both_ends(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(
        f"{REPORTS}/sales",
        headers=auth_headers,
        params={"preset": "custom", "date_from": "2026-01-01"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_date_range"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
async def test_reports_export_as_csv_and_xlsx(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    await _sell(
        client, auth_headers, seeded, [{"product_id": product["id"], "quantity": "1"}], pay="2.00"
    )

    csv = await client.get(
        f"{REPORTS}/sales/export", headers=auth_headers, params={"format": "csv", "preset": "today"}
    )
    assert csv.status_code == 200, csv.text
    assert csv.headers["content-type"].startswith("text/csv")
    assert "attachment" in csv.headers["content-disposition"]
    assert "Total sales" in csv.text

    xlsx = await client.get(
        f"{REPORTS}/sales/export",
        headers=auth_headers,
        params={"format": "xlsx", "preset": "today"},
    )
    assert xlsx.status_code == 200, xlsx.text
    assert "spreadsheetml" in xlsx.headers["content-type"]
    assert xlsx.content[:2] == b"PK"  # a zip, i.e. a real workbook

    html = await client.get(
        f"{REPORTS}/financial/export",
        headers=auth_headers,
        params={"format": "html", "preset": "today"},
    )
    assert html.status_code == 200, html.text
    assert html.headers["content-type"].startswith("text/html")
    assert "Financial report" in html.text


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_a_cashier_cannot_read_or_export_reports(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    forbidden = await client.get(f"{REPORTS}/sales", headers=cashier_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "insufficient_permissions"

    export = await client.get(
        f"{REPORTS}/financial/export", headers=cashier_headers, params={"format": "csv"}
    )
    assert export.status_code == 403
