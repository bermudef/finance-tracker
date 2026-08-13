"""CSV export/import for transactions."""
from __future__ import annotations

import io
import csv

API = "/api/v1"


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


async def _upload(auth_client, csv_text: str) -> tuple:
    return await auth_client.post(
        f"{API}/transactions/import",
        files={"file": ("transactions.csv", csv_text.encode("utf-8"), "text/csv")},
    )


async def test_export_requires_auth(client):
    assert (await client.get(f"{API}/transactions/export")).status_code == 401


async def test_import_requires_auth(client):
    resp = await client.post(
        f"{API}/transactions/import",
        files={"file": ("t.csv", b"date,amount\n2026-01-01,-1", "text/csv")},
    )
    assert resp.status_code == 401


async def test_export_round_trips_through_import(auth_client):
    ctx = await _setup(auth_client)
    await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": ctx["account_id"],
            "category_id": ctx["category_id"],
            "date": "2026-06-01",
            "amount": -45.25,
            "description": "Whole Foods",
            "merchant": "WF",
        },
    )
    await auth_client.post(
        f"{API}/transactions",
        json={"account_id": ctx["account_id"], "date": "2026-06-02", "amount": 2500.0},
    )

    exported = await auth_client.get(f"{API}/transactions/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")

    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert len(rows) == 2
    assert rows[0]["date"] == "2026-06-01"
    assert rows[0]["amount"] == "-45.25"
    assert rows[0]["category"] == "Groceries"
    assert rows[0]["account"] == "Checking"
    assert rows[1]["category"] == ""
    assert rows[1]["amount"] == "2500.00"

    # Round-trip: wipe and re-import from the exported bytes.
    tx_list = (await auth_client.get(f"{API}/transactions")).json()
    for tx in tx_list:
        await auth_client.delete(f"{API}/transactions/{tx['id']}")
    assert (await auth_client.get(f"{API}/transactions")).json() == []

    resp = await _upload(auth_client, exported.text)
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 2
    assert body["skipped"] == 0

    reimported = (await auth_client.get(f"{API}/transactions")).json()
    assert len(reimported) == 2
    by_desc = {t["description"]: t for t in reimported}
    assert by_desc["Whole Foods"]["category_name"] == "Groceries"
    assert by_desc["Whole Foods"]["amount"] == -45.25


async def test_import_matches_accounts_and_categories_case_insensitively(auth_client):
    await _setup(auth_client)
    resp = await _upload(
        auth_client,
        "date,amount,description,category,account,status\n"
        "2026-07-01,-12.34,coffee,GROCERIES,checking,pending\n"
        "2026-07-02,1000,salary,,,cleared\n",
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 2

    txs = (await auth_client.get(f"{API}/transactions")).json()
    coffee = next(t for t in txs if t["description"] == "coffee")
    assert coffee["category_name"] == "Groceries"
    assert coffee["account_name"] == "Checking"
    assert coffee["status"] == "pending"
    salary = next(t for t in txs if t["description"] == "salary")
    assert salary["status"] == "cleared"
    assert salary["amount"] == 1000


async def test_import_skips_bad_rows_and_reports_them(auth_client):
    ctx = await _setup(auth_client)
    resp = await _upload(
        auth_client,
        "date,amount,description,category,account\n"
        "2026-07-01,-10,ok,,\n"
        "not-a-date,-5,bad-date,,\n"
        "2026-07-01,0,zero-amount,,\n"
        "2026-07-01,-10,no-such-cat,nope,,\n"
        "2026-07-01,-10,no-such-account,,nope\n",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    assert body["skipped"] == 4
    errors = {e["row"] for e in body["errors"]}
    assert errors == {3, 4, 5, 6}
    assert "no-such-cat" in str(body["errors"]) or any(
        "category" in e["error"] for e in body["errors"]
    )
    assert (await auth_client.get(f"{API}/transactions")).json()[0]["description"] == "ok"
    assert ctx["account_id"]  # silence unused-var lint; ctx used implicitly above


async def test_import_requires_date_and_amount_columns(auth_client):
    await _setup(auth_client)
    resp = await _upload(auth_client, "description,merchant\nhello,world\n")
    assert resp.status_code == 400


async def test_import_rejects_non_utf8(auth_client):
    await _setup(auth_client)
    resp = await auth_client.post(
        f"{API}/transactions/import",
        files={"file": ("bad.csv", b"\xff\xfe\x00binary", "text/csv")},
    )
    assert resp.status_code == 400


async def test_import_requires_at_least_one_account(auth_client):
    resp = await _upload(auth_client, "date,amount\n2026-07-01,-10\n")
    assert resp.status_code == 400
