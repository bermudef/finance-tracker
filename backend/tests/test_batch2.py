"""Batch 2 features: recurring transactions, CSV exports, budget rollover,
savings milestones, investment benchmark, net worth series, loss harvesting,
email verification."""
from __future__ import annotations

import os
from datetime import date, timedelta

from app.services.benchmark import build_comparison, load_spx_series
from app.services.net_worth import compute_net_worth_series
from app.services.tax_estimation import suggest_loss_harvesting

API = "/api/v1"


async def _setup_account_category(client):
    """Create an account + expense category; returns (account_id, category_id)."""
    account = await client.post(f"{API}/accounts", json={"name": "Checking", "type": "checking", "opening_balance": 1000})
    assert account.status_code == 200, account.text
    category = await client.post(f"{API}/categories", json={"name": "Groceries", "type": "expense"})
    assert category.status_code == 200, category.text
    return account.json()["id"], category.json()["id"]


# ---------- Recurring transactions ----------

async def test_recurring_process_posts_and_advances(auth_client):
    account_id, category_id = await _setup_account_category(auth_client)

    create = await auth_client.post(
        f"{API}/recurring-transactions",
        json={
            "name": "Netflix",
            "account_id": account_id,
            "category_id": category_id,
            "amount": -15.99,
            "frequency": "monthly",
            "next_date": date.today().isoformat(),
        },
    )
    assert create.status_code == 201, create.text
    item_id = create.json()["id"]

    process = await auth_client.post(f"{API}/recurring-transactions/process")
    assert process.status_code == 200, process.text
    assert process.json()["posted"] == 1

    # The transaction exists with the recurring item's date and description,
    # and is linked back to its schedule so the UI can badge/filter it.
    txs = await auth_client.get(f"{API}/transactions")
    assert txs.status_code == 200, txs.text
    posted = [t for t in txs.json() if t.get("merchant") == "Netflix"]
    assert len(posted) == 1
    assert posted[0]["amount"] == -15.99
    assert posted[0]["description"] == "Recurring: Netflix"
    assert posted[0]["recurring_id"] == item_id
    assert posted[0]["is_recurring"] is True
    assert posted[0]["recurring_name"] == "Netflix"

    # next_date rolled forward to the next month, same day-of-month (clamped
    # to the last valid day like bill scheduling).
    detail = await auth_client.get(f"{API}/recurring-transactions")
    item = next(i for i in detail.json() if i["id"] == item_id)
    today = date.today()
    next_year = today.year + (today.month - 1 + 1) // 12
    next_month = (today.month - 1 + 1) % 12 + 1
    days_in_next_month = (date(next_year, next_month + 1, 1) - date(next_year, next_month, 1)).days if next_month < 12 else (date(next_year + 1, 1, 1) - date(next_year, 12, 1)).days
    expected = date(next_year, next_month, min(today.day, days_in_next_month))
    assert item["next_date"] == expected.isoformat()

    # Processing again is a no-op until the next due date arrives.
    again = await auth_client.post(f"{API}/recurring-transactions/process")
    assert again.json()["posted"] == 0


async def test_overdue_recurring_posts_current_period(auth_client):
    """An overdue schedule materializes in the current period, not on its
    stale back-dated next_date, so the row is visible near the top of the
    feed (and the badge shows) instead of buried months ago."""
    account_id, _ = await _setup_account_category(auth_client)
    stale = date.today() - timedelta(days=90)

    create = await auth_client.post(
        f"{API}/recurring-transactions",
        json={
            "name": "Streaming bundle",
            "account_id": account_id,
            "amount": -15.99,
            "frequency": "monthly",
            "next_date": stale.isoformat(),
        },
    )
    assert create.status_code == 201, create.text

    process = await auth_client.post(f"{API}/recurring-transactions/process")
    assert process.status_code == 200, process.text
    assert process.json()["posted"] == 1

    txs = await auth_client.get(f"{API}/transactions")
    posted = [t for t in txs.json() if t.get("merchant") == "Streaming bundle"]
    assert len(posted) == 1
    assert posted[0]["is_recurring"] is True

    today = date.today()
    recent = posted[0]["date"]
    assert date.fromisoformat(recent) <= today
    assert (today - date.fromisoformat(recent)).days <= 31  # same period, not 3 months back

    # Schedule rolled forward past the posted date, not re-anchored to today.
    detail = await auth_client.get(f"{API}/recurring-transactions")
    item = next(i for i in detail.json() if i["id"] == create.json()["id"])
    assert item["next_date"] > recent


async def test_recurring_inactive_items_are_skipped(auth_client):
    account_id, _ = await _setup_account_category(auth_client)
    create = await auth_client.post(
        f"{API}/recurring-transactions",
        json={
            "name": "Paused gym",
            "account_id": account_id,
            "amount": -30.0,
            "frequency": "monthly",
            "next_date": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    item_id = create.json()["id"]
    paused = await auth_client.put(
        f"{API}/recurring-transactions/{item_id}", json={"is_active": False}
    )
    assert paused.status_code == 200, paused.text

    process = await auth_client.post(f"{API}/recurring-transactions/process")
    assert process.json()["posted"] == 0


async def test_process_does_not_duplicate_existing_occurrence(auth_client):
    """If the current period's occurrence is already posted for a schedule
    (e.g. the seed backfilled it), processing must not post a second row that
    would double-count expenses like mortgage + car + utilities."""
    account_id, _ = await _setup_account_category(auth_client)

    create = await auth_client.post(
        f"{API}/recurring-transactions",
        json={
            "name": "Internet",
            "account_id": account_id,
            "amount": -60.0,
            "frequency": "monthly",
            "next_date": (date.today() - timedelta(days=30)).isoformat(),
        },
    )
    assert create.status_code == 201, create.text
    item_id = create.json()["id"]

    # First processing run posts the current-period occurrence.
    first = await auth_client.post(f"{API}/recurring-transactions/process")
    assert first.status_code == 200, first.text
    assert first.json()["posted"] == 1

    txs = await auth_client.get(f"{API}/transactions")
    internet = [t for t in txs.json() if t.get("merchant") == "Internet"]
    assert len(internet) == 1
    assert internet[0]["recurring_id"] == item_id
    posted_date = internet[0]["date"]

    # Simulate the seed/reseed path: a transaction already exists for the
    # schedule on that date. Reprocessing must not create a duplicate.
    await auth_client.post(f"{API}/recurring-transactions/process")
    txs = await auth_client.get(f"{API}/transactions")
    internet = [t for t in txs.json() if t.get("merchant") == "Internet"]
    assert len(internet) == 1
    assert internet[0]["date"] == posted_date


async def test_due_recurring_auto_posts_on_login(client, user_data):
    """Due recurring items materialize into transactions when the user logs in,
    so recurring payments show up in the transactions feed without a manual
    'Process now' click."""
    reg = await client.post(f"{API}/auth/register", json=user_data)
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    account = await client.post(
        f"{API}/accounts",
        json={"name": "Checking", "type": "checking", "opening_balance": 0},
        headers=headers,
    )
    account_id = account.json()["id"]

    create = await client.post(
        f"{API}/recurring-transactions",
        json={
            "name": "Online storage",
            "account_id": account_id,
            "amount": -9.99,
            "frequency": "monthly",
            "next_date": (date.today() - timedelta(days=3)).isoformat(),
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text

    txs = await client.get(f"{API}/transactions", headers=headers)
    assert txs.json() == []  # nothing posted yet

    login = await client.post(
        f"{API}/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    )
    assert login.status_code == 200, login.text

    txs = await client.get(f"{API}/transactions", headers=headers)
    posted = [t for t in txs.json() if t.get("merchant") == "Online storage"]
    assert len(posted) == 1
    assert posted[0]["is_recurring"] is True


# ---------- CSV exports ----------

async def test_accounts_export_csv(auth_client):
    account_id, _ = await _setup_account_category(auth_client)
    await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": account_id,
            "amount": -25.0,
            "date": date.today().isoformat(),
            "description": "Coffee",
        },
    )

    resp = await auth_client.get(f"{API}/accounts/export")
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert body.startswith("name,type,currency,opening_balance,current_balance,is_active")
    assert "Checking" in body
    assert "975.00" in body  # 1000 opening - 25 spent


async def test_budgets_export_csv(auth_client):
    await auth_client.post(f"{API}/budgets", json={"name": "Fun", "amount": 200.0, "rollover": True})
    resp = await auth_client.get(f"{API}/budgets/export")
    assert resp.status_code == 200, resp.text
    assert resp.text.startswith("name,category,amount,period,rollover")
    assert "Fun,,200.00,monthly,True" in resp.text


# ---------- Budget rollover ----------

async def test_budget_rollover_carries_last_month_leftover(auth_client):
    _, category_id = await _setup_account_category(auth_client)
    # Spend 40 of the 100 budget in the PREVIOUS month.
    today = date.today()
    last_month_end = today.replace(day=1) - timedelta(days=1)
    account_id, _ = await _setup_account_category(auth_client)
    await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": account_id,
            "category_id": category_id,
            "amount": -40.0,
            "date": last_month_end.isoformat(),
            "description": "Last month groceries",
        },
    )
    budget = await auth_client.post(
        f"{API}/budgets",
        json={"name": "Groceries", "category_id": category_id, "amount": 100.0, "rollover": True},
    )
    assert budget.status_code == 200, budget.text

    dash = await auth_client.get(f"{API}/dashboard")
    row = next(b for b in dash.json()["budgets"] if b["id"] == budget.json()["id"])
    assert row["rollover"] is True
    assert row["carryover"] == 60.0
    assert row["effective_amount"] == 160.0


async def test_budget_without_rollover_has_no_carryover(auth_client):
    budget = await auth_client.post(f"{API}/budgets", json={"name": "Fun", "amount": 100.0})
    assert budget.json()["rollover"] is False
    dash = await auth_client.get(f"{API}/dashboard")
    row = next(b for b in dash.json()["budgets"] if b["id"] == budget.json()["id"])
    assert row["carryover"] == 0.0
    assert row["effective_amount"] == 100.0


async def test_budget_update_toggles_rollover(auth_client):
    budget = await auth_client.post(f"{API}/budgets", json={"name": "Fun", "amount": 100.0})
    updated = await auth_client.put(
        f"{API}/budgets/{budget.json()['id']}", json={"rollover": True}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["rollover"] is True


# ---------- Savings goal milestones ----------

async def test_savings_goal_achievement_notification(auth_client):
    await auth_client.post(
        f"{API}/savings-goals",
        json={"name": "Emergency Fund", "target_amount": 5000.0, "current_amount": 5000.0},
    )
    generate = await auth_client.post(f"{API}/notifications/generate")
    assert generate.status_code == 200, generate.text
    titles = [n["title"] for n in generate.json()]
    assert "Savings goal achieved: Emergency Fund" in titles

    # Idempotent: generating again must not duplicate the milestone.
    again = await auth_client.post(f"{API}/notifications/generate")
    count = sum(1 for n in again.json() if n["type"] == "savings_milestone")
    assert count == 0


async def test_savings_goal_75_percent_milestone(auth_client):
    await auth_client.post(
        f"{API}/savings-goals",
        json={"name": "Vacation", "target_amount": 4000.0, "current_amount": 3000.0},
    )
    generate = await auth_client.post(f"{API}/notifications/generate")
    titles = [n["title"] for n in generate.json()]
    assert "Savings goal 75% reached: Vacation" in titles


# ---------- Investment benchmark ----------

def test_benchmark_returns_known_spx_window():
    series = load_spx_series()
    window = series[-13:]  # 1 year of closes (12 intervals)
    start = window[0]["close"]
    end = window[-1]["close"]
    expected = (end - start) / start * 100

    result = build_comparison(cost_basis=10_000, current_value=11_000, years=1)
    assert result["user_return_pct"] == 10.0
    assert abs(result["benchmark_return_pct"] - expected) < 0.01
    assert result["series"][0]["index"] == 100.0
    assert result["series"][-1]["index"] == round(end / start * 100, 2)
    assert len(result["series"]) == 13


def test_benchmark_years_clamped_to_dataset():
    result = build_comparison(cost_basis=0, current_value=0, years=99)
    assert result["years"] == 10  # dataset supports at most 10 years
    assert result["user_return_pct"] == 0.0


# ---------- Net worth series ----------

async def test_net_worth_series_reflects_transaction_history(auth_client):
    account_id, _ = await _setup_account_category(auth_client)  # opening 1000
    today = date.today()
    month_start = today.replace(day=1)
    two_months_ago_end = month_start - timedelta(days=1)
    last_month_start = two_months_ago_end.replace(day=1)

    # +200 two months ago, -100 last month.
    await auth_client.post(
        f"{API}/transactions",
        json={"account_id": account_id, "amount": 200.0, "date": last_month_start.isoformat(), "description": "Paycheck"},
    )
    await auth_client.post(
        f"{API}/transactions",
        json={"account_id": account_id, "amount": -100.0, "date": month_start.isoformat(), "description": "Rent"},
    )

    dash = await auth_client.get(f"{API}/dashboard")
    series = dash.json()["net_worth_series"]
    assert series["months"] == 12
    assert len(series["series"]) == 12

    points = series["series"]
    assert points[-2]["net_worth"] == 1200.0  # opening 1000 + paycheck 200
    assert points[-1]["net_worth"] == 1100.0  # minus rent 100
    assert points[-1]["net_worth"] == dash.json()["net_worth"]


# ---------- Tax-loss harvesting ----------

def test_loss_harvesting_flags_losers_only():
    holdings = [
        {"name": "Tech ETF", "symbol": "TECH", "cost_basis": 1000.0, "current_value": 700.0, "type": "etf"},
        {"name": "Green Stock", "symbol": "GRN", "cost_basis": 500.0, "current_value": 550.0, "type": "stock"},
        {"name": "Old Co", "symbol": "OLD", "cost_basis": 2000.0, "current_value": 1400.0, "type": "stock"},
        {"name": "Tiny Loss", "symbol": "TNY", "cost_basis": 100.0, "current_value": 90.0, "type": "stock"},
    ]
    candidates = suggest_loss_harvesting(holdings)
    assert len(candidates) == 2  # Green Stock gains and Tiny Loss (< $100) excluded
    assert candidates[0]["name"] == "Old Co"  # sorted by loss size
    assert candidates[0]["unrealized_loss"] == 600.0
    assert candidates[0]["est_tax_savings"] == 90.0  # 15% of loss


async def test_loss_harvesting_endpoint(auth_client):
    await auth_client.post(
        f"{API}/investments",
        json={"name": "Bad Fund", "type": "etf", "cost_basis": 1000.0, "current_value": 800.0},
    )
    resp = await auth_client.get(f"{API}/tools/loss-harvesting")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["candidates"]) == 1
    assert resp.json()["candidates"][0]["unrealized_loss"] == 200.0


# ---------- Email verification ----------

async def test_register_returns_verification_token_and_verify_flow(client, user_data):
    register = await client.post(f"{API}/auth/register", json=user_data)
    assert register.status_code == 201, register.text
    body = register.json()
    assert body["email_verified"] is False
    assert body["verification_token"]  # dev mode returns the token

    token = body["verification_token"]
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    me = await client.get(f"{API}/auth/me", headers=headers)
    assert me.json()["email_verified"] is False

    verify = await client.get(f"{API}/auth/verify-email", params={"token": token})
    assert verify.status_code == 200, verify.text
    assert verify.json()["status"] == "verified"

    me = await client.get(f"{API}/auth/me", headers=headers)
    assert me.json()["email_verified"] is True

    # The token is single-use.
    second = await client.get(f"{API}/auth/verify-email", params={"token": token})
    assert second.status_code == 404


async def test_verify_email_rejects_unknown_token(client):
    resp = await client.get(f"{API}/auth/verify-email", params={"token": "not-a-real-token"})
    assert resp.status_code == 404
