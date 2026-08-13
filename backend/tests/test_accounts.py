"""Accounts CRUD + ownership isolation tests."""
from __future__ import annotations

import csv
import io

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


async def test_accounts_export_excludes_pending_from_current_balance(auth_client):
    created = await auth_client.post(f"{API}/accounts", json=ACCOUNT_PAYLOAD)
    account_id = created.json()["id"]
    await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": account_id,
            "date": "2026-08-01",
            "amount": 200.0,
            "description": "Posted deposit",
            "status": "posted",
        },
    )
    await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": account_id,
            "date": "2026-08-02",
            "amount": -50.0,
            "description": "Pending card hold",
            "status": "pending",
        },
    )

    exported = await auth_client.get(f"{API}/accounts/export")
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert rows[0]["current_balance"] == "1200.00"
