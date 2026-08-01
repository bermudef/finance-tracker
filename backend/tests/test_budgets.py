"""Budgets CRUD + ownership isolation tests."""
from __future__ import annotations

API = "/api/v1"


async def test_budgets_require_auth(client):
    assert (await client.get(f"{API}/budgets")).status_code == 401


async def test_create_and_list_budget(auth_client):
    category = await auth_client.post(
        f"{API}/categories", json={"name": "Dining", "type": "expense"}
    )
    resp = await auth_client.post(
        f"{API}/budgets",
        json={"name": "Dining budget", "category_id": category.json()["id"], "amount": 300},
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == 300.0

    listed = await auth_client.get(f"{API}/budgets")
    assert len(listed.json()) == 1


async def test_budget_with_foreign_category_rejected(auth_client, second_user_headers):
    foreign_cat = await auth_client.post(
        f"{API}/categories", json={"name": "Their Cat", "type": "expense"}
    )
    resp = await auth_client.post(
        f"{API}/budgets",
        headers=second_user_headers,
        json={"name": "Sneaky", "category_id": foreign_cat.json()["id"], "amount": 100},
    )
    assert resp.status_code == 404


async def test_delete_budget(auth_client):
    created = await auth_client.post(
        f"{API}/budgets", json={"name": "Fun", "amount": 100}
    )
    resp = await auth_client.delete(f"{API}/budgets/{created.json()['id']}")
    assert resp.status_code == 200
    assert (await auth_client.get(f"{API}/budgets")).json() == []


async def test_cannot_delete_others_budget(auth_client, second_user_headers):
    created = await auth_client.post(
        f"{API}/budgets", json={"name": "Fun", "amount": 100}
    )
    resp = await auth_client.delete(
        f"{API}/budgets/{created.json()['id']}", headers=second_user_headers
    )
    assert resp.status_code == 404
