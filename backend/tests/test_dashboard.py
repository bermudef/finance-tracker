"""Dashboard aggregation correctness tests."""
from __future__ import annotations

from datetime import date, timedelta

API = "/api/v1"

TODAY = date.today()
MONTH_START = TODAY.replace(day=1)
PREV_MONTH_START = (MONTH_START - timedelta(days=1)).replace(day=1)


async def _seed(auth_client, balances, transactions):
    """Create accounts with opening balances and post transactions."""
    account_ids = {}
    for name, balance in balances.items():
        resp = await auth_client.post(
            f"{API}/accounts", json={"name": name, "type": "checking", "opening_balance": balance}
        )
        account_ids[name] = resp.json()["id"]

    category_ids = {}
    for name in ("Groceries", "Salary"):
        resp = await auth_client.post(
            f"{API}/categories", json={"name": name, "type": "expense" if name == "Groceries" else "income"}
        )
        category_ids[name] = resp.json()["id"]

    for txn in transactions:
        await auth_client.post(
            f"{API}/transactions",
            json={
                "account_id": account_ids[txn["account"]],
                "category_id": category_ids[txn["category"]],
                "date": txn["date"].isoformat(),
                "amount": txn["amount"],
                "description": txn["description"],
            },
        )
    return account_ids, category_ids


async def test_empty_dashboard(auth_client):
    resp = await auth_client.get(f"{API}/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_balance"] == 0.0
    assert body["accounts"] == []
    assert body["monthly"]["income"] == 0.0
    assert body["monthly"]["expense"] == 0.0
    assert body["spending_by_category"] == []
    assert len(body["monthly_series"]) == 6


async def test_balances_include_opening_and_transactions(auth_client):
    await _seed(
        auth_client,
        balances={"Checking": 5000, "Savings": 10000},
        transactions=[
            {"account": "Checking", "category": "Salary", "date": TODAY, "amount": 8000,
             "description": "Salary"},
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -471.05,
             "description": "Groceries"},
        ],
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()

    assert body["total_balance"] == 5000 + 10000 + 8000 - 471.05
    balances = {a["name"]: a["balance"] for a in body["accounts"]}
    assert balances["Checking"] == 5000 + 8000 - 471.05
    assert balances["Savings"] == 10000.0


async def test_monthly_income_expense_and_category_spending(auth_client):
    await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Salary", "date": TODAY, "amount": 8000,
             "description": "Salary"},
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -350.75,
             "description": "Store A"},
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -120.30,
             "description": "Store B"},
        ],
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    monthly = body["monthly"]

    assert monthly["income"] == 8000.0
    assert monthly["expense"] == 471.05
    assert monthly["net"] == 8000.0 - 471.05

    spending = body["spending_by_category"]
    assert len(spending) == 1
    assert spending[0]["name"] == "Groceries"
    assert spending[0]["amount"] == 471.05


async def test_income_never_counts_as_category_spending(auth_client):
    """A salary mis-tagged as an expense category must not distort spending."""
    await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": 8000,
             "description": "Oops salary in groceries"},
        ],
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["spending_by_category"] == []


async def test_previous_month_comparison(auth_client):
    await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Salary", "date": PREV_MONTH_START, "amount": 7000,
             "description": "Last month salary"},
        ],
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["monthly"]["last_month_income"] == 7000.0


async def test_budget_spent_tracking(auth_client):
    _, category_ids = await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -150,
             "description": "Groceries"},
        ],
    )
    await auth_client.post(
        f"{API}/budgets",
        json={"name": "Groceries budget", "category_id": category_ids["Groceries"], "amount": 300},
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()

    assert len(body["budgets"]) == 1
    budget = body["budgets"][0]
    assert budget["amount"] == 300.0
    assert budget["spent"] == 150.0


async def test_dashboard_isolated_between_users(auth_client, second_user_headers):
    await _seed(
        auth_client,
        balances={"Checking": 5000},
        transactions=[
            {"account": "Checking", "category": "Salary", "date": TODAY, "amount": 1000,
             "description": "Salary"},
        ],
    )
    other = (await auth_client.get(f"{API}/dashboard", headers=second_user_headers)).json()
    assert other["total_balance"] == 0.0
    assert other["accounts"] == []
    assert other["monthly"]["income"] == 0.0
