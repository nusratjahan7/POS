"""Category hierarchy and brand metadata (MODULE 05)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

CATEGORIES = "/api/v1/categories"
BRANDS = "/api/v1/brands"


async def _create_category(client: AsyncClient, headers: dict[str, str], **overrides: Any) -> Any:
    payload: dict[str, Any] = {"name": "Coffee"}
    payload.update(overrides)
    response = await client.post(CATEGORIES, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------
async def test_a_child_category_reports_its_parent(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    parent = await _create_category(client, auth_headers, name="Drinks")

    child = await _create_category(client, auth_headers, name="Hot Drinks", parent_id=parent["id"])

    assert child["parent_id"] == parent["id"]
    assert child["parent"]["name"] == "Drinks"
    assert child["parent"]["slug"] == "drinks"


async def test_top_level_categories_have_no_parent(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    body = await _create_category(client, auth_headers)

    assert body["parent_id"] is None
    assert body["parent"] is None


async def test_tree_nests_children_under_their_parents(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    drinks = await _create_category(client, auth_headers, name="Drinks")
    hot = await _create_category(client, auth_headers, name="Hot", parent_id=drinks["id"])
    await _create_category(client, auth_headers, name="Iced", parent_id=drinks["id"])
    await _create_category(client, auth_headers, name="Bakery")

    tree = (await client.get(f"{CATEGORIES}/tree", headers=auth_headers)).json()

    roots = {node["name"]: node for node in tree}
    assert set(roots) == {"Drinks", "Bakery"}
    assert {child["name"] for child in roots["Drinks"]["children"]} == {"Hot", "Iced"}
    assert roots["Drinks"]["children"][0]["parent_id"] == drinks["id"]
    # Grandchildren hang off their own node, not the root.
    assert hot["id"] in {child["id"] for child in roots["Drinks"]["children"]}


async def test_a_category_cannot_be_its_own_parent(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    category = await _create_category(client, auth_headers)

    response = await client.patch(
        f"{CATEGORIES}/{category['id']}",
        headers=auth_headers,
        json={"parent_id": category["id"]},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "category_cycle"


async def test_a_category_cannot_move_under_its_own_descendant(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    root = await _create_category(client, auth_headers, name="Root")
    child = await _create_category(client, auth_headers, name="Child", parent_id=root["id"])
    grandchild = await _create_category(
        client, auth_headers, name="Grandchild", parent_id=child["id"]
    )

    response = await client.patch(
        f"{CATEGORIES}/{root['id']}",
        headers=auth_headers,
        json={"parent_id": grandchild["id"]},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "category_cycle"


async def test_unknown_parent_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        CATEGORIES,
        headers=auth_headers,
        json={"name": "Orphan", "parent_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_parent_category"


async def test_promoting_a_child_to_top_level_clears_the_parent(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    parent = await _create_category(client, auth_headers, name="Drinks")
    child = await _create_category(client, auth_headers, name="Hot", parent_id=parent["id"])

    response = await client.patch(
        f"{CATEGORIES}/{child['id']}", headers=auth_headers, json={"parent_id": None}
    )

    assert response.status_code == 200, response.text
    assert response.json()["parent_id"] is None
    assert response.json()["parent"] is None


async def test_a_category_with_children_cannot_be_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    parent = await _create_category(client, auth_headers, name="Drinks")
    await _create_category(client, auth_headers, name="Hot", parent_id=parent["id"])

    response = await client.delete(f"{CATEGORIES}/{parent['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_has_children"


# ---------------------------------------------------------------------------
# Filters, search, sort, pagination
# ---------------------------------------------------------------------------
async def test_parent_and_top_level_filters(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    parent = await _create_category(client, auth_headers, name="Drinks")
    await _create_category(client, auth_headers, name="Hot", parent_id=parent["id"])
    await _create_category(client, auth_headers, name="Bakery")

    children = await client.get(
        CATEGORIES, headers=auth_headers, params={"parent_id": parent["id"]}
    )
    top = await client.get(CATEGORIES, headers=auth_headers, params={"top_level": "true"})

    assert children.json()["total"] == 1
    assert children.json()["items"][0]["name"] == "Hot"
    assert {item["name"] for item in top.json()["items"]} == {"Drinks", "Bakery"}


async def test_search_covers_name_and_slug(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _create_category(client, auth_headers, name="Specialty Coffee")

    async def total_for(term: str) -> int:
        response = await client.get(CATEGORIES, headers=auth_headers, params={"search": term})
        return int(response.json()["total"])

    assert await total_for("specialty") == 1
    assert await total_for("coffee") == 1  # matches the slug and the name
    assert await total_for("nothing") == 0


async def test_status_filter_and_sorting_and_pagination(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    for name in ("Alpha", "Bravo", "Charlie"):
        await _create_category(client, auth_headers, name=name)
    inactive = await _create_category(client, auth_headers, name="Delta")
    await client.patch(
        f"{CATEGORIES}/{inactive['id']}", headers=auth_headers, json={"is_active": False}
    )

    active = await client.get(CATEGORIES, headers=auth_headers, params={"is_active": "true"})
    assert active.json()["total"] == 3

    descending = await client.get(CATEGORIES, headers=auth_headers, params={"sort": "-name"})
    names = [item["name"] for item in descending.json()["items"]]
    assert names == sorted(names, reverse=True)

    paged = await client.get(CATEGORIES, headers=auth_headers, params={"page_size": 2, "page": 2})
    assert paged.json()["total"] == 4
    assert paged.json()["pages"] == 2
    assert len(paged.json()["items"]) == 2


async def test_category_image_round_trips(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await _create_category(
        client, auth_headers, image_url="/media/11111111111111111111111111111111.png"
    )
    assert created["image_url"].endswith(".png")

    cleared = await client.patch(
        f"{CATEGORIES}/{created['id']}", headers=auth_headers, json={"image_url": None}
    )
    assert cleared.json()["image_url"] is None


async def test_duplicate_category_name_is_still_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _create_category(client, auth_headers, name="Coffee")

    response = await client.post(CATEGORIES, headers=auth_headers, json={"name": "coffee"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_name_taken"


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------
async def test_brand_logo_round_trips_and_can_be_cleared(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await client.post(
        BRANDS,
        headers=auth_headers,
        json={"name": "Lavazza", "logo_url": "/media/22222222222222222222222222222222.png"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["logo_url"].endswith(".png")
    assert body["slug"] == "lavazza"

    cleared = await client.patch(
        f"{BRANDS}/{body['id']}", headers=auth_headers, json={"logo_url": None}
    )
    assert cleared.json()["logo_url"] is None


async def test_brand_search_filter_and_pagination(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    for name in ("Lavazza", "Illy", "Segafredo"):
        assert (
            await client.post(BRANDS, headers=auth_headers, json={"name": name})
        ).status_code == 201

    hidden = (await client.post(BRANDS, headers=auth_headers, json={"name": "Hidden"})).json()
    await client.patch(f"{BRANDS}/{hidden['id']}", headers=auth_headers, json={"is_active": False})

    search = await client.get(BRANDS, headers=auth_headers, params={"search": "illy"})
    assert search.json()["total"] == 1

    active = await client.get(BRANDS, headers=auth_headers, params={"is_active": "true"})
    assert active.json()["total"] == 3

    paged = await client.get(BRANDS, headers=auth_headers, params={"page_size": 2})
    assert paged.json()["total"] == 4
    assert len(paged.json()["items"]) == 2


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_taxonomy_endpoints_require_authentication(client: AsyncClient) -> None:
    for path in (CATEGORIES, f"{CATEGORIES}/tree", BRANDS):
        response = await client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"


async def test_inventory_manager_can_read_but_not_write_the_taxonomy(
    client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    assert (await client.get(CATEGORIES, headers=inventory_manager_headers)).status_code == 200
    assert (
        await client.get(f"{CATEGORIES}/tree", headers=inventory_manager_headers)
    ).status_code == 200
    assert (await client.get(BRANDS, headers=inventory_manager_headers)).status_code == 200

    denied = await client.post(CATEGORIES, headers=inventory_manager_headers, json={"name": "Nope"})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "insufficient_permissions"


async def test_a_user_without_catalog_permission_is_denied(
    client: AsyncClient, login_as: Any, db_session: Any
) -> None:
    """Categories and brands are gated on catalog:read, which comes from a role."""
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email="no-catalog@example.com",
        hashed_password=hash_password("NoCatalog1!"),
        full_name="No Catalog",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    headers = await login_as(user.email, "NoCatalog1!")
    response = await client.get(CATEGORIES, headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"
