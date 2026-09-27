"""Store foundation: business, branches, registers and payment methods."""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient

BUSINESS = "/api/v1/business"
BRANCHES = "/api/v1/branches"
REGISTERS = "/api/v1/registers"
PAYMENTS = "/api/v1/payment-methods"


def _register(branch_id: Any, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Till 1",
        "branch_id": str(branch_id),
        "is_active": True,
        "default_opening_balance": "100.00",
        "require_opening_balance": True,
        "allow_opening_balance_override": False,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Business
# ---------------------------------------------------------------------------
async def test_business_profile_is_returned_with_the_seeded_defaults(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    body = (await client.get(BUSINESS, headers=auth_headers)).json()

    assert body["name"] == "My Business"
    assert body["currency"] == "USD"
    assert body["timezone"] == "UTC"
    assert body["tax_enabled"] is False
    assert body["default_tax_rate"] == "0.000"


async def test_business_update_normalises_currency_and_persists_tax_settings(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.patch(
        BUSINESS,
        headers=auth_headers,
        json={
            "name": "Acme Retail",
            "currency": "bdt",
            "timezone": "Asia/Dhaka",
            "tax_enabled": True,
            "tax_inclusive": False,
            "tax_label": "VAT",
            "default_tax_rate": "15.000",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Acme Retail"
    assert body["currency"] == "BDT"
    assert body["timezone"] == "Asia/Dhaka"
    assert body["tax_label"] == "VAT"
    assert body["default_tax_rate"] == "15.000"

    # Persisted, not merely echoed.
    assert (await client.get(BUSINESS, headers=auth_headers)).json()["name"] == "Acme Retail"


async def test_business_rejects_an_unknown_time_zone(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.patch(BUSINESS, headers=auth_headers, json={"timezone": "Mars/Phobos"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_business_rejects_an_out_of_range_tax_rate(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.patch(BUSINESS, headers=auth_headers, json={"default_tax_rate": "150"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_business_rejects_a_malformed_currency(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.patch(BUSINESS, headers=auth_headers, json={"currency": "US"})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Branches link to the business
# ---------------------------------------------------------------------------
async def test_a_new_branch_belongs_to_the_default_business(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    response = await client.post(
        BRANCHES, headers=auth_headers, json={"name": "Uptown", "code": "UPT"}
    )

    assert response.status_code == 201, response.text
    assert response.json()["business_id"] == str(seeded.business.id)


async def test_a_branch_with_registers_cannot_be_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # A fresh branch (no staff assigned) isolates the register guard.
    branch = (
        await client.post(BRANCHES, headers=auth_headers, json={"name": "Uptown", "code": "UPT"})
    ).json()
    created = await client.post(REGISTERS, headers=auth_headers, json=_register(branch["id"]))
    assert created.status_code == 201, created.text

    response = await client.delete(f"{BRANCHES}/{branch['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "branch_has_registers"


# ---------------------------------------------------------------------------
# Registers
# ---------------------------------------------------------------------------
async def test_register_round_trip_carries_its_branch_and_opening_settings(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    body = (
        await client.post(REGISTERS, headers=auth_headers, json=_register(seeded.branch.id))
    ).json()

    assert body["name"] == "Till 1"
    assert body["branch"]["id"] == str(seeded.branch.id)
    assert body["branch"]["code"] == seeded.branch.code
    assert body["default_opening_balance"] == "100.00"
    assert body["require_opening_balance"] is True
    assert body["allow_opening_balance_override"] is False


async def test_register_names_are_unique_per_branch(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    await client.post(REGISTERS, headers=auth_headers, json=_register(seeded.branch.id))

    duplicate = await client.post(
        REGISTERS, headers=auth_headers, json=_register(seeded.branch.id, name="till 1")
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "register_name_taken"


async def test_register_requires_a_known_branch(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(REGISTERS, headers=auth_headers, json=_register(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_branch"


async def test_registers_can_be_filtered_by_branch_and_updated(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    created = (
        await client.post(REGISTERS, headers=auth_headers, json=_register(seeded.branch.id))
    ).json()

    listed = await client.get(
        REGISTERS, headers=auth_headers, params={"branch_id": str(seeded.branch.id)}
    )
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == created["id"]

    updated = await client.patch(
        f"{REGISTERS}/{created['id']}",
        headers=auth_headers,
        json={"name": "Till 2", "default_opening_balance": "250.50", "is_active": False},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Till 2"
    assert updated.json()["default_opening_balance"] == "250.50"
    assert updated.json()["is_active"] is False

    assert (
        await client.delete(f"{REGISTERS}/{created['id']}", headers=auth_headers)
    ).status_code == 204
    assert (
        await client.get(f"{REGISTERS}/{created['id']}", headers=auth_headers)
    ).status_code == 404


async def test_register_options_expose_id_name_and_branch(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    await client.post(REGISTERS, headers=auth_headers, json=_register(seeded.branch.id))

    options = (await client.get(f"{REGISTERS}/options", headers=auth_headers)).json()

    assert len(options) == 1
    assert set(options[0]) == {"id", "name", "branch_id"}
    assert options[0]["branch_id"] == str(seeded.branch.id)


# ---------------------------------------------------------------------------
# Payment methods
# ---------------------------------------------------------------------------
async def test_default_payment_methods_are_seeded(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    items = (await client.get(PAYMENTS, headers=auth_headers)).json()["items"]
    codes = {item["code"] for item in items}

    assert {"CASH", "CARD", "BKASH", "NAGAD", "BANK", "OTHER"} <= codes

    cash = next(item for item in items if item["code"] == "CASH")
    assert cash["kind"] == "cash"
    assert cash["opens_cash_drawer"] is True
    assert cash["is_system"] is True


async def test_payment_method_options_are_active_only(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    cash_id = str(seeded.payment_methods["CASH"].id)
    await client.patch(f"{PAYMENTS}/{cash_id}", headers=auth_headers, json={"is_active": False})

    options = (await client.get(f"{PAYMENTS}/options", headers=auth_headers)).json()

    assert "CASH" not in {option["code"] for option in options}
    assert "CARD" in {option["code"] for option in options}


async def test_a_custom_payment_method_can_be_created_and_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await client.post(
        PAYMENTS,
        headers=auth_headers,
        json={"name": "Gift card", "code": "gift", "kind": "other", "sort_order": 9},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["code"] == "GIFT"
    assert body["is_system"] is False

    assert (
        await client.delete(f"{PAYMENTS}/{body['id']}", headers=auth_headers)
    ).status_code == 204


async def test_duplicate_payment_code_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        PAYMENTS, headers=auth_headers, json={"name": "Cash 2", "code": "CASH"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "payment_code_taken"


async def test_builtin_payment_methods_cannot_be_deleted_or_re_coded(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    cash_id = str(seeded.payment_methods["CASH"].id)

    delete = await client.delete(f"{PAYMENTS}/{cash_id}", headers=auth_headers)
    assert delete.status_code == 403
    assert delete.json()["error"]["code"] == "payment_method_immutable"

    recode = await client.patch(
        f"{PAYMENTS}/{cash_id}", headers=auth_headers, json={"code": "MONEY"}
    )
    assert recode.status_code == 403
    assert recode.json()["error"]["code"] == "payment_method_immutable"

    # Non-identifying fields remain editable.
    rename = await client.patch(
        f"{PAYMENTS}/{cash_id}", headers=auth_headers, json={"name": "Cash on hand"}
    )
    assert rename.status_code == 200
    assert rename.json()["name"] == "Cash on hand"


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_settings_endpoints_require_authentication(client: AsyncClient) -> None:
    for path in (BUSINESS, BRANCHES, REGISTERS, PAYMENTS):
        response = await client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"


async def test_cashier_can_read_store_settings_but_not_change_them(
    client: AsyncClient, cashier_headers: dict[str, str], seeded: Any
) -> None:
    assert (await client.get(BUSINESS, headers=cashier_headers)).status_code == 200
    assert (await client.get(REGISTERS, headers=cashier_headers)).status_code == 200
    assert (await client.get(PAYMENTS, headers=cashier_headers)).status_code == 200

    for method, path, payload in (
        ("patch", BUSINESS, {"name": "Hacked"}),
        ("post", REGISTERS, _register(seeded.branch.id, name="Rogue")),
        ("post", PAYMENTS, {"name": "Rogue", "code": "ROGUE"}),
    ):
        response = await getattr(client, method)(path, headers=cashier_headers, json=payload)
        assert response.status_code == 403, path
        assert response.json()["error"]["code"] == "insufficient_permissions"


async def test_manager_can_read_business_but_cannot_edit_it(
    client: AsyncClient, manager_headers: dict[str, str], seeded: Any
) -> None:
    assert (await client.get(BUSINESS, headers=manager_headers)).status_code == 200

    denied = await client.patch(BUSINESS, headers=manager_headers, json={"name": "Manager Edited"})
    assert denied.status_code == 403

    # ...but managing registers is part of the day-to-day job.
    created = await client.post(
        REGISTERS, headers=manager_headers, json=_register(seeded.branch.id, name="Manager Till")
    )
    assert created.status_code == 201, created.text


async def test_inventory_manager_cannot_read_store_settings(
    client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    response = await client.get(BUSINESS, headers=inventory_manager_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"
