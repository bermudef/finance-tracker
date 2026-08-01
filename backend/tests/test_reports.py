"""Monthly report endpoint tests."""
from __future__ import annotations

from datetime import date, timedelta

API = "/api/v1"

TODAY = date.today()
THIS_YEAR, THIS_MONTH = TODAY.year, TODAY.month
MONTH_START = TODAY.replace(day=1)
LAST_MONTH_START = (MONTH_START - timedelta(days=1)).replace(day=1)
LAST_MONTH = LAST_MONTH_START.month
LAST_YEAR = LAST_MONTH_START.year


async def _seed(auth_client, transactions):
    """Create accounts/categories and post transactions in bulk."""
    account_ids = {}
    for name in ("Checking", "Savings"):
        resp = await auth_client.post(
            f"{API}/accounts", json={"name": name, "type": "checking"}
        )
        account_ids[name] = resp.json()["id"]

    category_ids = {}
    for name in ("Groceries", "Dining", "Salary"):
        resp = await auth_client.post(
            f"{API}/categories",
            json={"name": name, "type": "expense" if name != "Salary" else "income"},
        )
        category_ids[name] = resp.json()["id"]

    for txn in transactions:
        await auth_client.post(
            f"{API}/transactions",
            json={
                "account_id": account_ids.get(txn.get("account"), account_ids["Checking"]),
                "category_id": category_ids.get(txn["category"]) if txn.get("category") else None,
                "date": txn["date"].isoformat(),
                "amount": txn["amount"],
                "description": txn.get("description", ""),
                "merchant": txn.get("merchant"),
            },
        )
    return account_ids, category_ids


async def test_report_requires_auth(client):
    assert (await client.get(f"{API}/reports/monthly")).status_code == 401


async def test_empty_month_report(auth_client):
    resp = await auth_client.get(f"{API}/reports/monthly")
    assert resp.status_code == 200
    body = resp.json()
    assert body["income"] == 0.0
    assert body["expense"] == 0.0
    assert body["net"] == 0.0
    assert body["by_category"] == []
    assert body["by_account"] == []
    assert body["top_merchants"] == []
    assert len(body["daily_series"]) == 31  # defaults to the current month


async def test_monthly_report_aggregates(auth_client):
    _, category_ids = await _seed(
        auth_client,
        [
            {"account": "Checking", "category": "Salary", "date": TODAY, "amount": 8000,
             "description": "Salary", "merchant": "Acme"},
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -200,
             "description": "Store", "merchant": "Whole Foods"},
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -50,
             "description": "Store 2", "merchant": "Whole Foods"},
            {"account": "Savings", "category": "Dining", "date": TODAY, "amount": -75,
             "description": "Lunch", "merchant": "Cafe"},
        ],
    )
    body = (
        await auth_client.get(
            f"{API}/reports/monthly?year={THIS_YEAR}&month={THIS_MONTH}"
        )
    ).json()

    assert body["income"] == 8000.0
    assert body["expense"] == 325.0
    assert body["net"] == 8000.0 - 325.0

    by_cat = {c["name"]: c for c in body["by_category"]}
    assert by_cat["Groceries"]["amount"] == 250.0
    assert by_cat["Groceries"]["pct"] == round(250.0 / 325.0 * 100, 1)
    assert by_cat["Dining"]["amount"] == 75.0

    by_acct = {a["name"]: a for a in body["by_account"]}
    assert by_acct["Checking"]["income"] == 8000.0
    assert by_acct["Checking"]["expense"] == 250.0
    assert by_acct["Checking"]["net"] == 7750.0
    assert by_acct["Savings"]["net"] == -75.0

    assert [m["merchant"] for m in body["top_merchants"]] == ["Whole Foods", "Cafe"]
    assert body["top_merchants"][0]["amount"] == 250.0

    day = TODAY.day
    assert body["daily_series"][day - 1]["income"] == 8000.0
    assert body["daily_series"][day - 1]["expense"] == -325.0
    assert len(body["daily_series"]) == (TODAY.replace(day=28) + timedelta(days=4)).replace(day=1).day - 1 or 28


async def test_report_uncategorized_line(auth_client):
    await _seed(
        auth_client,
        [
            {"date": TODAY, "amount": -30, "description": "No category"},
        ],
    )
    body = (
        await auth_client.get(
            f"{API}/reports/monthly?year={THIS_YEAR}&month={THIS_MONTH}"
        )
    ).json()
    names = {c["name"] for c in body["by_category"]}
    assert "Uncategorized" in names
    uncat = next(c for c in body["by_category"] if c["name"] == "Uncategorized")
    assert uncat["amount"] == 30.0
    assert uncat["pct"] == 100.0


async def test_report_respects_month_boundaries(auth_client):
    next_month_start = (MONTH_START.replace(day=28) + timedelta(days=4)).replace(day=1)
    await _seed(
        auth_client,
        [
            # In scope: this month
            {"date": TODAY, "amount": -100, "description": "In scope"},
            # Out of scope: previous month
            {"date": LAST_MONTH_START, "amount": -999, "description": "Prev month"},
            # Out of scope: next month
            {"date": next_month_start, "amount": -888, "description": "Next month"},
        ],
    )
    body = (
        await auth_client.get(
            f"{API}/reports/monthly?year={THIS_YEAR}&month={THIS_MONTH}"
        )
    ).json()
    assert body["expense"] == 100.0

    prev_body = (
        await auth_client.get(
            f"{API}/reports/monthly?year={LAST_YEAR}&month={LAST_MONTH}"
        )
    ).json()
    assert prev_body["expense"] == 999.0
    # Previous-month block compares against the month before the requested one.
    assert prev_body["previous"]["income"] == 0.0


async def test_report_top_merchants_capped_at_ten(auth_client):
    tx = []
    for i in range(1, 15):
        tx.append(
            {"date": TODAY, "amount": -float(i), "description": f"Merchant {i}",
             "merchant": f"Merchant {i}"}
        )
    await _seed(auth_client, tx)
    body = (
        await auth_client.get(
            f"{API}/reports/monthly?year={THIS_YEAR}&month={THIS_MONTH}"
        )
    ).json()
    assert len(body["top_merchants"]) == 10
    assert body["top_merchants"][0]["merchant"] == "Merchant 14"


async def test_report_invalid_month(auth_client):
    resp = await auth_client.get(f"{API}/reports/monthly?month=13")
    assert resp.status_code == 422
    resp = await auth_client.get(f"{API}/reports/monthly?month=0")
    assert resp.status_code == 422


async def test_report_isolated_between_users(auth_client, second_user_headers):
    await _seed(
        auth_client,
        [{"date": TODAY, "amount": -100, "description": "Mine"}],
    )
    other = (
        await auth_client.get(
            f"{API}/reports/monthly?year={THIS_YEAR}&month={THIS_MONTH}",
            headers=second_user_headers,
        )
    ).json()
    assert other["income"] == 0.0
    assert other["expense"] == 0.0
    assert other["by_category"] == []
