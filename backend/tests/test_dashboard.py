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
                "category_id": category_ids[txn["category"]] if txn.get("category") else None,
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
    assert body["upcoming_bills"] == []
    assert body["health"]["grade"] in {"Excellent", "Good", "Fair", "Needs work"}
    assert 0 <= body["health"]["score"] <= 100


async def test_dashboard_upcoming_bills(auth_client):
    """Bills roll to their next occurrence and surface on the dashboard."""
    await auth_client.post(
        f"{API}/bills",
        json={"name": "Netflix", "amount": 15.99, "due_date": (TODAY - timedelta(days=20)).isoformat(), "frequency": "monthly", "auto_pay": True},
    )
    await auth_client.post(
        f"{API}/bills",
        json={"name": "Rent", "amount": 1850.00, "due_date": (TODAY + timedelta(days=2)).isoformat(), "frequency": "monthly", "auto_pay": False},
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    upcoming = body["upcoming_bills"]
    # Netflix rolled forward to ~10 days out; Rent is 2 days out and first.
    assert [b["name"] for b in upcoming] == ["Rent", "Netflix"]
    assert upcoming[0]["days_until"] == 2
    assert upcoming[0]["amount"] == 1850.0
    assert upcoming[1]["next_due_date"] > (TODAY - timedelta(days=20)).isoformat()


async def test_dashboard_monthly_totals_ignore_next_month_transactions(auth_client):
    next_month_start = (MONTH_START.replace(day=28) + timedelta(days=4)).replace(day=1)
    await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Salary", "date": TODAY, "amount": 8000,
             "description": "This month salary"},
            {"account": "Checking", "category": "Salary", "date": next_month_start, "amount": 9000,
             "description": "Next month salary"},
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -100,
             "description": "This month groceries"},
            {"account": "Checking", "category": "Groceries", "date": next_month_start, "amount": -250,
             "description": "Next month groceries"},
        ],
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["monthly"]["income"] == 8000.0
    assert body["monthly"]["expense"] == 100.0
    assert body["monthly"]["net"] == 7900.0
    assert body["spending_by_category"] == [
        {"name": "Groceries", "amount": 100.0, "color": None}
    ]


async def test_dashboard_upcoming_bills_only_shows_next_30_days(auth_client):
    await auth_client.post(
        f"{API}/bills",
        json={"name": "Rent", "amount": 1850.00, "due_date": (TODAY + timedelta(days=2)).isoformat(), "frequency": "monthly"},
    )
    await auth_client.post(
        f"{API}/bills",
        json={"name": "Insurance", "amount": 120.00, "due_date": (TODAY + timedelta(days=45)).isoformat(), "frequency": "monthly"},
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert [b["name"] for b in body["upcoming_bills"]] == ["Rent"]


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
    assert body["current_month_series"][TODAY.day - 1]["balance"] == 8000.0 - 471.05
    assert body["current_month_series"][TODAY.day - 1]["expense"] == 471.05


async def test_dashboard_current_month_series_runs_within_month(auth_client):
    earlier = TODAY.replace(day=1)
    later = TODAY.replace(day=min(TODAY.day, 2))
    await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Salary", "date": earlier, "amount": 3000,
             "description": "Salary"},
            {"account": "Checking", "category": "Groceries", "date": later, "amount": -200,
             "description": "Groceries"},
        ],
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    series = body["current_month_series"]
    assert series[0]["balance"] == 3000.0
    expected_day_2_balance = 2800.0 if later.day == 2 else 3000.0
    expected_day_2_expense = 200.0 if later.day == 2 else 0.0
    assert series[1]["balance"] == expected_day_2_balance
    assert series[1]["expense"] == expected_day_2_expense


async def test_dashboard_current_month_series_falls_back_to_latest_month_with_data(auth_client):
    last_month_day = PREV_MONTH_START.replace(day=1)
    await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Salary", "date": last_month_day, "amount": 4000,
             "description": "Last month salary"},
            {"account": "Checking", "category": "Groceries", "date": last_month_day, "amount": -250,
             "description": "Last month groceries"},
        ],
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["monthly"]["income"] == 0.0
    assert body["monthly"]["expense"] == 0.0
    assert body["current_month_series_label"] == PREV_MONTH_START.strftime("%B %Y")
    assert body["current_month_series"][0]["balance"] == 3750.0


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
    assert budget["progress_pct"] == 50.0

    # A single expense in a budget is treated as a fixed monthly charge rather
    # than a daily run-rate that repeats all month.
    assert budget["projected"] == 150.0
    assert budget["status"] == "on_track"


async def test_budget_status_flags_over_budget(auth_client):
    """Spending 120% of the budget is 'at risk', regardless of the date."""
    _, category_ids = await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -120,
             "description": "Groceries"},
        ],
    )
    await auth_client.post(
        f"{API}/budgets",
        json={"name": "Tight", "category_id": category_ids["Groceries"], "amount": 100},
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    budget = body["budgets"][0]
    assert budget["spent"] == 120.0
    assert budget["progress_pct"] == 120.0
    assert budget["status"] == "at_risk"


async def test_fixed_monthly_budget_does_not_extrapolate_single_payment(auth_client):
    """One large monthly payment should not be projected as daily recurring spend."""
    _, category_ids = await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -1800,
             "description": "Mortgage"},
        ],
    )
    await auth_client.post(
        f"{API}/budgets",
        json={"name": "Housing", "category_id": category_ids["Groceries"], "amount": 1800},
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    budget = body["budgets"][0]
    assert budget["spent"] == 1800.0
    assert budget["projected"] == 1800.0
    assert budget["status"] == "at_risk"


async def test_budget_status_guards_zero_amount(auth_client):
    """A $0 budget with any spending is over; with none it's on track."""
    _, category_ids = await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[],
    )
    await auth_client.post(
        f"{API}/budgets",
        json={"name": "Zero", "category_id": category_ids["Groceries"], "amount": 0},
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["budgets"][0]["status"] == "on_track"


async def test_general_budget_tracks_all_expenses(auth_client):
    """A budget without a category is general: it sums every expense this month,
    including categorized ones (not just uncategorized)."""
    _, category_ids = await _seed(
        auth_client,
        balances={"Checking": 0},
        transactions=[
            {"account": "Checking", "category": "Groceries", "date": TODAY, "amount": -150,
             "description": "Categorized expense"},
            {"account": "Checking", "date": TODAY, "amount": -50,
             "description": "Uncategorized expense"},
        ],
    )
    await auth_client.post(
        f"{API}/budgets",
        json={"name": "General", "amount": 500},
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    general = next(b for b in body["budgets"] if b["name"] == "General")
    assert general["spent"] == 200.0
    assert general["progress_pct"] == 40.0


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


async def test_dashboard_excludes_pending_transactions_from_aggregates(auth_client):
    await _seed(
        auth_client,
        balances={"Checking": 5000},
        transactions=[
            {"account": "Checking", "category": "Salary", "date": TODAY, "amount": 1000,
             "description": "Posted salary"},
        ],
    )
    accounts = (await auth_client.get(f"{API}/accounts")).json()
    cats = (await auth_client.get(f"{API}/categories")).json()
    checking = next(a for a in accounts if a["name"] == "Checking")["id"]
    groceries = next(c for c in cats if c["name"] == "Groceries")["id"]
    await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": checking,
            "category_id": groceries,
            "date": TODAY.isoformat(),
            "amount": -250.0,
            "description": "Pending groceries",
            "status": "pending",
        },
    )

    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["total_balance"] == 6000.0
    assert body["monthly"]["income"] == 1000.0
    assert body["monthly"]["expense"] == 0.0
    assert body["monthly"]["net"] == 1000.0
    assert body["spending_by_category"] == []


async def test_net_worth_assets_minus_liabilities(auth_client):
    await _seed(
        auth_client,
        balances={"Checking": 5000},
        transactions=[],
    )
    await auth_client.post(
        f"{API}/investments",
        json={"name": "VTI", "type": "etf", "cost_basis": 1000, "current_value": 1500},
    )
    await auth_client.post(
        f"{API}/credit-cards",
        json={"name": "Visa", "balance": 2000, "credit_limit": 5000, "apr": 20},
    )
    await auth_client.post(
        f"{API}/debts",
        json={"name": "Student Loan", "type": "student", "principal": 10000, "interest_rate": 5},
    )

    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["total_balance"] == 5000.0
    assert body["net_worth"] == 5000 + 1500 - 2000 - 10000  # assets - liabilities
    assert body["debt"]["total"] == 12000.0
    assert body["investments"]["total_value"] == 1500.0
    assert body["investments"]["total_cost_basis"] == 1000.0
    assert body["investments"]["gain_loss"] == 500.0


async def test_net_worth_series_excludes_inactive_liabilities(auth_client):
    await _seed(
        auth_client,
        balances={"Checking": 5000},
        transactions=[],
    )
    card = await auth_client.post(
        f"{API}/credit-cards",
        json={"name": "Visa", "balance": 2000, "credit_limit": 5000},
    )
    debt = await auth_client.post(
        f"{API}/debts",
        json={"name": "Student Loan", "type": "student", "principal": 10000},
    )
    await auth_client.put(f"{API}/credit-cards/{card.json()['id']}", json={"is_active": False})
    await auth_client.put(f"{API}/debts/{debt.json()['id']}", json={"is_active": False})

    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["net_worth"] == 5000.0
    assert body["net_worth_series"]["series"][-1]["net_worth"] == 5000.0


async def test_debt_breakdown_by_type(auth_client):
    await auth_client.post(
        f"{API}/debts", json={"name": "Car", "type": "auto", "principal": 15000}
    )
    await auth_client.post(
        f"{API}/debts", json={"name": "House", "type": "mortgage", "principal": 200000}
    )
    await auth_client.post(
        f"{API}/debts", json={"name": "Second Car", "type": "auto", "principal": 5000}
    )
    await auth_client.post(
        f"{API}/credit-cards", json={"name": "Visa", "balance": 500}
    )

    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["debt"]["total"] == 220500.0
    assert body["debt"]["by_type"]["auto"] == 20000.0
    assert body["debt"]["by_type"]["mortgage"] == 200000.0
    assert body["debt"]["by_type"]["credit_card"] == 500.0


async def test_savings_goal_progress(auth_client):
    await auth_client.post(
        f"{API}/savings-goals",
        json={"name": "Emergency Fund", "target_amount": 10000, "current_amount": 2500},
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert len(body["savings_goals"]) == 1
    goal = body["savings_goals"][0]
    assert goal["progress_pct"] == 25.0


async def test_inactive_savings_goals_excluded(auth_client):
    created = await auth_client.post(
        f"{API}/savings-goals",
        json={"name": "Old Goal", "target_amount": 5000, "current_amount": 5000},
    )
    await auth_client.put(
        f"{API}/savings-goals/{created.json()['id']}", json={"is_active": False}
    )
    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["savings_goals"] == []
