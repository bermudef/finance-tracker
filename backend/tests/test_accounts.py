"""Accounts CRUD + ownership isolation tests."""
from __future__ import annotations

API = "/api/v1"

ACCOUNT_PAYLOAD = {"name": "Checking", "type": "checking", "opening_balance": 1000}


async def test_accounts_require_auth(client):
    assert (await client.get(f"{API}/accounts")).status_code == 401
    assert (
        await client.post(f"{API}/accounts", json=ACCOUNT_PAYLOAD)
    ).status_code == 401


async def test_create_and_list_account(auth_client):
    created = await auth_client.post(f"{API}/accounts", json=ACCOUNT_PAYLOAD)
    assert created.status_code == 200
    body = created.json()
    assert body["name"] == "Checking"
    assert body["type"] == "checking"
    assert body["opening_balance"] == 1000.0
    assert body["is_active"] is True

    listed = await auth_client.get(f"{API}/accounts")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_accounts_isolated_between_users(auth_client, second_user_headers):
    await auth_client.post(f"{API}/accounts", json=ACCOUNT_PAYLOAD)

    other = await auth_client.get(f"{API}/accounts", headers=second_user_headers)
    assert other.status_code == 200
    assert other.json() == []


async def test_delete_own_account(auth_client):
    created = await auth_client.post(f"{API}/accounts", json=ACCOUNT_PAYLOAD)
    account_id = created.json()["id"]

    resp = await auth_client.delete(f"{API}/accounts/{account_id}")
    assert resp.status_code == 200
    assert (await auth_client.get(f"{API}/accounts")).json() == []


async def test_cannot_delete_others_account(auth_client, second_user_headers):
    created = await auth_client.post(f"{API}/accounts", json=ACCOUNT_PAYLOAD)
    account_id = created.json()["id"]

    resp = await auth_client.delete(
        f"{API}/accounts/{account_id}", headers=second_user_headers
    )
    assert resp.status_code == 404  # not visible -> not found (no info leak)

    assert len((await auth_client.get(f"{API}/accounts")).json()) == 1


async def test_delete_missing_account_404(auth_client):
    resp = await auth_client.delete(f"{API}/accounts/99999")
    assert resp.status_code == 404
