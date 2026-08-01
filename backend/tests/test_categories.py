"""Categories CRUD + ownership isolation tests."""
from __future__ import annotations

API = "/api/v1"

CATEGORY_PAYLOAD = {"name": "Groceries", "type": "expense"}


async def test_categories_require_auth(client):
    assert (await client.get(f"{API}/categories")).status_code == 401
    assert (
        await client.post(f"{API}/categories", json=CATEGORY_PAYLOAD)
    ).status_code == 401


async def test_create_and_list_categories(auth_client):
    created = await auth_client.post(f"{API}/categories", json=CATEGORY_PAYLOAD)
    assert created.status_code == 200
    assert created.json()["name"] == "Groceries"

    listed = await auth_client.get(f"{API}/categories")
    assert len(listed.json()) == 1


async def test_filter_by_type(auth_client):
    await auth_client.post(f"{API}/categories", json=CATEGORY_PAYLOAD)  # expense
    await auth_client.post(
        f"{API}/categories", json={"name": "Salary", "type": "income"}
    )

    expenses = await auth_client.get(f"{API}/categories?type=expense")
    assert [c["name"] for c in expenses.json()] == ["Groceries"]

    income = await auth_client.get(f"{API}/categories?type=income")
    assert [c["name"] for c in income.json()] == ["Salary"]


async def test_categories_isolated_between_users(auth_client, second_user_headers):
    await auth_client.post(f"{API}/categories", json=CATEGORY_PAYLOAD)
    other = await auth_client.get(f"{API}/categories", headers=second_user_headers)
    assert other.json() == []


async def test_subcategory_with_own_parent(auth_client):
    parent = await auth_client.post(f"{API}/categories", json=CATEGORY_PAYLOAD)
    child = await auth_client.post(
        f"{API}/categories",
        json={"name": "Produce", "type": "expense", "parent_id": parent.json()["id"]},
    )
    assert child.status_code == 200
    assert child.json()["parent_id"] == parent.json()["id"]


async def test_subcategory_with_foreign_parent_rejected(auth_client, second_user_headers):
    parent = await auth_client.post(f"{API}/categories", json=CATEGORY_PAYLOAD)
    parent_id = parent.json()["id"]

    resp = await auth_client.post(
        f"{API}/categories",
        headers=second_user_headers,
        json={"name": "Sneaky", "type": "expense", "parent_id": parent_id},
    )
    assert resp.status_code == 404


async def test_delete_category(auth_client):
    created = await auth_client.post(f"{API}/categories", json=CATEGORY_PAYLOAD)
    resp = await auth_client.delete(f"{API}/categories/{created.json()['id']}")
    assert resp.status_code == 200
    assert (await auth_client.get(f"{API}/categories")).json() == []


async def test_cannot_delete_others_category(auth_client, second_user_headers):
    created = await auth_client.post(f"{API}/categories", json=CATEGORY_PAYLOAD)
    resp = await auth_client.delete(
        f"{API}/categories/{created.json()['id']}", headers=second_user_headers
    )
    assert resp.status_code == 404
