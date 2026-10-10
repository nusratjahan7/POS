"""MODULE 23 — stock transfers between branches.

The workflow is Draft → Requested → Approved → Shipped → Received (or
Cancelled before shipping). Stock moves at exactly two steps: the source drops
at **ship**, the destination rises at **receive**. Every other status leaves
inventory untouched, and an invalid quantity is refused rather than written.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from httpx import AsyncClient

TRANSFERS = "/api/v1/transfers"
BRANCHES = "/api/v1/branches"
USERS = "/api/v1/users"
PRODUCTS = "/api/v1/products"
MOVEMENTS = "/api/v1/inventory/movements"
STOCK = "/api/v1/inventory/stock"

MANAGER_PASSWORD = "TransferManager1!"


async def _branch(client: AsyncClient, headers: dict[str, str], code: str, name: str) -> dict:
    response = await client.post(BRANCHES, headers=headers, json={"name": name, "code": code})
    assert response.status_code == 201, response.text
    return response.json()


async def _product(client: AsyncClient, headers: dict[str, str], **overrides: Any) -> dict:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "TRF-BEAN",
        "minimum_stock": "0",
        "opening_stock": "0",
        "purchase_price": "1.00",
        "selling_price": "2.00",
    }
    payload.update(overrides)
    response = await client.post(PRODUCTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _stock_branch(
    client: AsyncClient, headers: dict[str, str], branch_id: Any, product_id: Any, quantity: str
) -> None:
    response = await client.post(
        MOVEMENTS,
        headers=headers,
        json={
            "product_id": str(product_id),
            "branch_id": str(branch_id),
            "quantity": quantity,
            "movement_type": "adjustment",
            "reference_type": "manual",
        },
    )
    assert response.status_code == 201, response.text


async def _on_hand(
    client: AsyncClient, headers: dict[str, str], branch_id: Any, product_id: Any
) -> str:
    response = await client.get(
        STOCK, headers=headers, params={"branch_id": str(branch_id), "page_size": 100}
    )
    assert response.status_code == 200, response.text
    for row in response.json()["items"]:
        if row["product"]["id"] == str(product_id):
            return str(row["quantity"])
    return "0.000"


def _body(from_branch: Any, to_branch: Any, items: list[dict], **overrides: Any) -> dict:
    payload: dict[str, Any] = {
        "from_branch_id": str(from_branch),
        "to_branch_id": str(to_branch),
        "items": items,
    }
    payload.update(overrides)
    return payload


async def _create(
    client: AsyncClient,
    headers: dict[str, str],
    from_branch: Any,
    to_branch: Any,
    product: Any,
    quantity: str = "3",
    **overrides: Any,
) -> Any:
    items = [{"product_id": product["id"], "quantity": quantity}]
    return await client.post(
        TRANSFERS, headers=headers, json=_body(from_branch, to_branch, items, **overrides)
    )


async def _action(
    client: AsyncClient, headers: dict[str, str], transfer_id: str, action: str, **json: Any
) -> Any:
    return await client.post(
        f"{TRANSFERS}/{transfer_id}/{action}", headers=headers, json=json or None
    )


def _error_code(response: Any) -> str:
    return response.json()["error"]["code"]


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------
async def test_a_new_transfer_starts_as_a_draft(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)

    created = await _create(client, auth_headers, seeded.branch.id, other["id"], product, "5")

    assert created.status_code == 201, created.text
    transfer = created.json()
    assert transfer["transfer_number"].startswith("TRF-")
    assert transfer["status"] == "draft"
    assert transfer["from_branch"]["id"] == str(seeded.branch.id)
    assert transfer["to_branch"]["id"] == other["id"]
    assert transfer["item_count"] == 1
    assert transfer["total_quantity"] == "5.000"
    assert transfer["items"][0]["product_name"] == "Beans"


async def test_same_branch_and_duplicate_products_are_rejected(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)

    same = await _create(client, auth_headers, seeded.branch.id, seeded.branch.id, product)
    assert same.status_code == 422

    duplicate = await client.post(
        TRANSFERS,
        headers=auth_headers,
        json=_body(
            seeded.branch.id,
            other["id"],
            [
                {"product_id": product["id"], "quantity": "1"},
                {"product_id": product["id"], "quantity": "2"},
            ],
        ),
    )
    assert duplicate.status_code == 422
    assert _error_code(duplicate) == "duplicate_transfer_item"


# ---------------------------------------------------------------------------
# The workflow and stock
# ---------------------------------------------------------------------------
async def test_stock_moves_at_ship_and_receive_only(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)
    await _stock_branch(client, auth_headers, seeded.branch.id, product["id"], "10")

    created = await _create(client, auth_headers, seeded.branch.id, other["id"], product, "3")
    tid = created.json()["id"]

    # DRAFT and APPROVED must not touch stock.
    approved = await _action(client, auth_headers, tid, "approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert await _on_hand(client, auth_headers, seeded.branch.id, product["id"]) == "10.000"
    assert await _on_hand(client, auth_headers, other["id"], product["id"]) == "0.000"

    # SHIP decreases the source only.
    shipped = await _action(client, auth_headers, tid, "ship")
    assert shipped.status_code == 200, shipped.text
    assert shipped.json()["status"] == "shipped"
    assert await _on_hand(client, auth_headers, seeded.branch.id, product["id"]) == "7.000"
    assert await _on_hand(client, auth_headers, other["id"], product["id"]) == "0.000"

    # RECEIVE increases the destination.
    received = await _action(client, auth_headers, tid, "receive")
    assert received.status_code == 200, received.text
    assert received.json()["status"] == "received"
    assert await _on_hand(client, auth_headers, other["id"], product["id"]) == "3.000"

    # Both legs are in the immutable ledger, tagged with the transfer.
    ledger = await client.get(
        MOVEMENTS, headers=auth_headers, params={"product_id": product["id"], "page_size": 100}
    )
    assert ledger.status_code == 200, ledger.text
    legs = [row for row in ledger.json()["items"] if row["reference_id"] == tid]
    assert {row["movement_type"] for row in legs} == {"transfer_out", "transfer_in"}
    assert all(row["reference_type"] == "transfer" for row in legs)
    out = next(row for row in legs if row["movement_type"] == "transfer_out")
    assert out["quantity"] == "-3.000"
    assert out["branch"]["id"] == str(seeded.branch.id)
    into = next(row for row in legs if row["movement_type"] == "transfer_in")
    assert into["quantity"] == "3.000"
    assert into["branch"]["id"] == other["id"]


async def test_shipping_more_than_the_source_holds_is_refused(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)
    await _stock_branch(client, auth_headers, seeded.branch.id, product["id"], "2")

    created = await _create(client, auth_headers, seeded.branch.id, other["id"], product, "5")
    tid = created.json()["id"]
    await _action(client, auth_headers, tid, "approve")

    refused = await _action(client, auth_headers, tid, "ship")
    assert refused.status_code == 422, refused.text
    assert _error_code(refused) == "insufficient_stock"

    # The status did not advance and no stock moved.
    current = await client.get(f"{TRANSFERS}/{tid}", headers=auth_headers)
    assert current.json()["status"] == "approved"
    assert await _on_hand(client, auth_headers, seeded.branch.id, product["id"]) == "2.000"
    assert await _on_hand(client, auth_headers, other["id"], product["id"]) == "0.000"


async def test_steps_out_of_order_are_rejected(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)
    tid = (await _create(client, auth_headers, seeded.branch.id, other["id"], product)).json()["id"]

    # Cannot receive or ship a draft.
    for action in ("receive", "ship"):
        response = await _action(client, auth_headers, tid, action)
        assert response.status_code == 400, response.text
        assert _error_code(response) == "transfer_invalid_transition"

    # Approve, ship, then a second approve is refused.
    await _action(client, auth_headers, tid, "approve")
    await _stock_branch(client, auth_headers, seeded.branch.id, product["id"], "5")
    await _action(client, auth_headers, tid, "ship")
    again = await _action(client, auth_headers, tid, "approve")
    assert again.status_code == 400
    assert _error_code(again) == "transfer_invalid_transition"


async def test_cancelling_before_shipping_leaves_stock_untouched(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)
    await _stock_branch(client, auth_headers, seeded.branch.id, product["id"], "10")

    created = await _create(client, auth_headers, seeded.branch.id, other["id"], product, "4")
    tid = created.json()["id"]
    await _action(client, auth_headers, tid, "approve")

    cancelled = await _action(client, auth_headers, tid, "cancel", reason="Wrong branch")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancel_reason"] == "Wrong branch"
    assert await _on_hand(client, auth_headers, seeded.branch.id, product["id"]) == "10.000"


async def test_a_shipped_transfer_cannot_be_cancelled(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)
    await _stock_branch(client, auth_headers, seeded.branch.id, product["id"], "5")
    tid = (await _create(client, auth_headers, seeded.branch.id, other["id"], product)).json()["id"]
    await _action(client, auth_headers, tid, "approve")
    await _action(client, auth_headers, tid, "ship")

    response = await _action(client, auth_headers, tid, "cancel")
    assert response.status_code == 400
    assert _error_code(response) == "transfer_invalid_transition"


async def test_a_draft_can_be_edited(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)
    response = await _create(client, auth_headers, seeded.branch.id, other["id"], product, "1")
    created = response.json()

    updated = await client.patch(
        f"{TRANSFERS}/{created['id']}",
        headers=auth_headers,
        json={"reference": "PO-42", "items": [{"product_id": product["id"], "quantity": "9"}]},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["reference"] == "PO-42"
    assert body["total_quantity"] == "9.000"


# ---------------------------------------------------------------------------
# Permissions and branch scope
# ---------------------------------------------------------------------------
async def test_the_endpoints_need_the_right_permission(
    client: AsyncClient,
    auth_headers: dict[str, str],
    cashier_headers: dict[str, str],
    seeded: SimpleNamespace,
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)

    assert (await client.get(TRANSFERS)).status_code == 401

    forbidden = await client.get(TRANSFERS, headers=cashier_headers)
    assert forbidden.status_code == 403
    assert _error_code(forbidden) == "insufficient_permissions"

    # A Cashier may not raise one either.
    created = await _create(client, cashier_headers, seeded.branch.id, other["id"], product)
    assert created.status_code == 403
    assert _error_code(created) == "insufficient_permissions"


async def test_an_inventory_manager_can_run_the_whole_workflow(
    client: AsyncClient,
    auth_headers: dict[str, str],
    login_as: Any,
    seeded: SimpleNamespace,
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)
    await _stock_branch(client, auth_headers, seeded.branch.id, product["id"], "5")

    # An inventory manager who covers both branches can run every step.
    created_user = await client.post(
        USERS,
        headers=auth_headers,
        json={
            "email": "stock.controller@example.com",
            "full_name": "Stock Controller",
            "password": MANAGER_PASSWORD,
            "role_ids": [str(seeded.roles["Inventory Manager"].id)],
            "branch_ids": [str(seeded.branch.id), other["id"]],
        },
    )
    assert created_user.status_code == 201, created_user.text
    headers = await login_as("stock.controller@example.com", MANAGER_PASSWORD)

    created = await _create(client, headers, seeded.branch.id, other["id"], product, "2")
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    for action in ("request", "approve", "ship", "receive"):
        response = await _action(client, headers, tid, action)
        assert response.status_code == 200, f"{action}: {response.text}"

    final = await client.get(f"{TRANSFERS}/{tid}", headers=headers)
    assert final.json()["status"] == "received"
    assert await _on_hand(client, headers, other["id"], product["id"]) == "2.000"


async def test_branch_scope_hides_and_blocks_other_branches(
    client: AsyncClient, auth_headers: dict[str, str], login_as: Any, seeded: SimpleNamespace
) -> None:
    east = await _branch(client, auth_headers, "EAST", "East Branch")
    west = await _branch(client, auth_headers, "WEST", "West Branch")
    product = await _product(client, auth_headers)
    await _stock_branch(client, auth_headers, seeded.branch.id, product["id"], "5")
    await _stock_branch(client, auth_headers, east["id"], product["id"], "5")

    # A transfer between two branches a scoped manager cannot see.
    away = (
        await _create(client, auth_headers, east["id"], west["id"], product, "1")
    ).json()
    # A transfer that touches the manager's own branch.
    mine = (
        await _create(client, auth_headers, seeded.branch.id, east["id"], product, "1")
    ).json()

    created_user = await client.post(
        USERS,
        headers=auth_headers,
        json={
            "email": "transfer.manager@example.com",
            "full_name": "Transfer Manager",
            "password": MANAGER_PASSWORD,
            "role_ids": [str(seeded.roles["Manager"].id)],
            "branch_ids": [str(seeded.branch.id)],
        },
    )
    assert created_user.status_code == 201, created_user.text
    scoped = await login_as("transfer.manager@example.com", MANAGER_PASSWORD)

    listed = await client.get(TRANSFERS, headers=scoped)
    assert listed.status_code == 200, listed.text
    ids = {row["id"] for row in listed.json()["items"]}
    assert mine["id"] in ids
    assert away["id"] not in ids

    # Reading the off-scope transfer is refused.
    denied = await client.get(f"{TRANSFERS}/{away['id']}", headers=scoped)
    assert denied.status_code == 403
    assert _error_code(denied) == "branch_forbidden"

    # Dispatching from a branch they do not hold is refused.
    blocked = await _create(client, scoped, east["id"], west["id"], product, "1")
    assert blocked.status_code == 403
    assert _error_code(blocked) == "branch_forbidden"
