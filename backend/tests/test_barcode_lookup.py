"""MODULE 21 — barcode lookup: the scanner's server contract.

The till matches a scanned code exactly on barcode (or SKU) and falls back to the
server. These tests pin that contract: an exact, case-insensitive hit; a substring
miss; and an unknown code returning an empty page.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
POS_CATALOG = "/api/v1/pos/catalog"

EAN = "4006381333931"


async def _product(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "BEAN-1",
        "barcode": EAN,
        "minimum_stock": "0",
        "opening_stock": "0",
        "purchase_price": "1.00",
        "selling_price": "2.00",
    }
    payload.update(overrides)
    response = await client.post(PRODUCTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_products_lookup_matches_an_exact_barcode(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _product(client, auth_headers)

    response = await client.get(PRODUCTS, headers=auth_headers, params={"barcode": EAN})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["sku"] == "BEAN-1"


async def test_barcode_lookup_is_case_insensitive(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _product(client, auth_headers, sku="WIDGET-1", barcode="code-abc")

    response = await client.get(PRODUCTS, headers=auth_headers, params={"barcode": "code-abc"})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1


async def test_barcode_lookup_is_not_a_substring_match(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _product(client, auth_headers)

    response = await client.get(PRODUCTS, headers=auth_headers, params={"barcode": "400638"})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0


async def test_unknown_barcode_returns_an_empty_page(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _product(client, auth_headers)

    response = await client.get(
        PRODUCTS, headers=auth_headers, params={"barcode": "does-not-exist"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


async def test_pos_catalog_resolves_a_scanned_barcode(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    await _product(client, auth_headers, opening_stock="5")

    response = await client.get(
        POS_CATALOG,
        headers=auth_headers,
        params={"barcode": EAN, "branch_id": str(seeded.branch.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["barcode"] == EAN
    # The till feed never carries cost fields.
    assert "purchase_price" not in body["items"][0]
