"""Transactions CRUD, filters, ownership isolation tests."""
from __future__ import annotations

from datetime import date, timedelta

API = "/api/v1"

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


async def _setup(auth_client) -> dict:
    account = await auth_client.post(
        f"{API}/accounts", json={"name": "Checking", "type": "checking"}
    )
    category = await auth_client.post(
        f"{API}/categories", json={"name": "Groceries", "type": "expense"}
    )
    return {
        "account_id": account.json()["id"],
        "category_id": category.json()["id"],
    }


async def test_transactions_require_auth(client):
    assert (await client.get(f"{API}/transactions")).status_code == 401


async def test_create_transaction_with_names(auth_client):
    ctx = await _setup(auth_client)
    resp = await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": ctx["account_id"],
            "category_id": ctx["category_id"],
            "date": TODAY,
            "amount": -45.25,
            "description": "Whole Foods",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["amount"] == -45.25
    assert body["account_name"] == "Checking"
    assert body["category_name"] == "Groceries"


async def test_create_requires_owned_account(auth_client, second_user_headers):
    foreign_account = await auth_client.post(
        f"{API}/accounts", json={"name": "Their Checking", "type": "checking"}
    )
    resp = await auth_client.post(
        f"{API}/transactions",
        headers=second_user_headers,
        json={
            "account_id": foreign_account.json()["id"],
            "date": TODAY,
            "amount": -10,
        },
    )
    assert resp.status_code == 404


async def test_create_requires_owned_category(auth_client, second_user_headers):
    ctx = await _setup(auth_client)
    foreign_cat = await auth_client.post(
        f"{API}/categories", json={"name": "Their Cat", "type": "expense"}
    )
    resp = await auth_client.post(
        f"{API}/transactions",
        headers=second_user_headers,
        json={
            "account_id": ctx["account_id"],
            "category_id": foreign_cat.json()["id"],
            "date": TODAY,
            "amount": -10,
        },
    )
    assert resp.status_code == 404


async def test_list_filters_by_account_category_date(auth_client):
    ctx = await _setup(auth_client)
    for amount in (-10, -20, -30):
        await auth_client.post(
            f"{API}/transactions",
            json={
                "account_id": ctx["account_id"],
                "category_id": ctx["category_id"],
                "date": TODAY,
                "amount": amount,
            },
        )

    by_account = await auth_client.get(f"{API}/transactions?account_id={ctx['account_id']}")
    assert len(by_account.json()) == 3

    by_category = await auth_client.get(
        f"{API}/transactions?category_id={ctx['category_id']}"
    )
    assert len(by_category.json()) == 3

    by_range = await auth_client.get(
        f"{API}/transactions?start={YESTERDAY}&end={TODAY}"
    )
    assert len(by_range.json()) == 3

    empty_range = await auth_client.get(
        f"{API}/transactions?start={TODAY}&end={YESTERDAY}"
    )
    assert empty_range.json() == []


async def test_update_transaction(auth_client):
    ctx = await _setup(auth_client)
    created = await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": ctx["account_id"],
            "category_id": ctx["category_id"],
            "date": TODAY,
            "amount": -45.25,
        },
    )
    tx_id = created.json()["id"]

    updated = await auth_client.put(
        f"{API}/transactions/{tx_id}",
        json={
            "account_id": ctx["account_id"],
            "category_id": ctx["category_id"],
            "date": TODAY,
            "amount": -39.99,
            "description": "Updated",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == -39.99
    assert updated.json()["description"] == "Updated"


async def test_cannot_update_others_transaction(auth_client, second_user_headers):
    ctx = await _setup(auth_client)
    created = await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": ctx["account_id"],
            "date": TODAY,
            "amount": -10,
        },
    )
    resp = await auth_client.put(
        f"{API}/transactions/{created.json()['id']}",
        headers=second_user_headers,
        json={
            "account_id": ctx["account_id"],
            "date": TODAY,
            "amount": -99,
        },
    )
    assert resp.status_code == 404


async def test_delete_transaction(auth_client):
    ctx = await _setup(auth_client)
    created = await auth_client.post(
        f"{API}/transactions",
        json={"account_id": ctx["account_id"], "date": TODAY, "amount": -10},
    )
    resp = await auth_client.delete(f"{API}/transactions/{created.json()['id']}")
    assert resp.status_code == 200
    assert (await auth_client.get(f"{API}/transactions")).json() == []


async def test_transactions_isolated_between_users(auth_client, second_user_headers):
    ctx = await _setup(auth_client)
    await auth_client.post(
        f"{API}/transactions",
        json={"account_id": ctx["account_id"], "date": TODAY, "amount": -10},
    )
    other = await auth_client.get(f"{API}/transactions", headers=second_user_headers)
    assert other.json() == []
