"""Financial health score: service unit tests + endpoint integration tests."""
from __future__ import annotations

from app.services.health_score import COMPONENTS, compute_health_score

API = "/api/v1"


def _perfect_metrics(**overrides):
    metrics = {
        "monthly_income": 8000.0,
        "monthly_expense": 4000.0,  # 50% savings rate
        "avg_monthly_expense": 4000.0,
        "liquid_assets": 60000.0,  # 15 months covered
        "monthly_debt_payments": 100.0,  # ~1% DTI
        "budget_statuses": {"on_track": 3, "at_risk": 0, "over": 0},
        "credit_balance": 500.0,
        "credit_limit": 20000.0,  # 2.5% utilization
        "credit_cards_count": 2,
        "goals_avg_progress": 1.0,
        "goals_count": 1,
        "as_of": "2026-07-31",
        "period_label": "July 2026",
    }
    metrics.update(overrides)
    return metrics


# ---------- service unit tests ----------

def test_perfect_metrics_score_100():
    result = compute_health_score(_perfect_metrics())
    assert result["score"] == 100
    assert result["grade"] == "Excellent"
    assert result["recommendations"] == []
    assert sum(s["weight"] for s in result["subscores"]) == 100


def test_weights_cover_all_components():
    result = compute_health_score(_perfect_metrics())
    keys = {s["key"] for s in result["subscores"]}
    assert keys == {c["key"] for c in COMPONENTS}


def test_low_savings_rate_drags_score():
    result = compute_health_score(_perfect_metrics(monthly_expense=7200.0))  # 10% saved
    savings = next(s for s in result["subscores"] if s["key"] == "savings_rate")
    assert savings["score"] == 50.0
    assert result["score"] < 100


def test_negative_savings_rate_scores_zero():
    result = compute_health_score(_perfect_metrics(monthly_expense=9000.0))  # overspending
    savings = next(s for s in result["subscores"] if s["key"] == "savings_rate")
    assert savings["score"] == 0.0


def test_emergency_fund_half_way():
    result = compute_health_score(_perfect_metrics(liquid_assets=12000.0))  # 3 months
    fund = next(s for s in result["subscores"] if s["key"] == "emergency_fund")
    assert fund["score"] == 50.0


def test_no_income_collapses_income_components():
    result = compute_health_score(_perfect_metrics(monthly_income=0.0))
    savings = next(s for s in result["subscores"] if s["key"] == "savings_rate")
    debt = next(s for s in result["subscores"] if s["key"] == "debt_burden")
    assert savings["score"] == 0.0
    assert debt["score"] == 0.0


def test_dti_36_percent_is_zero():
    result = compute_health_score(_perfect_metrics(monthly_debt_payments=2880.0))  # 36%
    debt = next(s for s in result["subscores"] if s["key"] == "debt_burden")
    assert debt["score"] == 0.0


def test_over_budget_scores_zero_for_adherence():
    result = compute_health_score(
        _perfect_metrics(budget_statuses={"on_track": 0, "at_risk": 0, "over": 2})
    )
    budget = next(s for s in result["subscores"] if s["key"] == "budget_adherence")
    assert budget["score"] == 0.0


def test_high_utilization_scores_zero():
    result = compute_health_score(
        _perfect_metrics(credit_balance=12000.0, credit_limit=20000.0)  # 60%
    )
    credit = next(s for s in result["subscores"] if s["key"] == "credit_utilization")
    assert credit["score"] == 0.0


def test_no_cards_is_neutral_not_punished():
    result = compute_health_score(_perfect_metrics(credit_cards_count=0))
    credit = next(s for s in result["subscores"] if s["key"] == "credit_utilization")
    assert credit["score"] == 70.0


def test_no_budgets_and_no_goals_are_neutral():
    result = compute_health_score(
        _perfect_metrics(
            budget_statuses={"on_track": 0, "at_risk": 0, "over": 0},
            goals_count=0,
            goals_avg_progress=None,
        )
    )
    budget = next(s for s in result["subscores"] if s["key"] == "budget_adherence")
    goals = next(s for s in result["subscores"] if s["key"] == "savings_goals")
    assert budget["score"] == 50.0
    assert goals["score"] == 50.0


def test_recommendations_target_weakest_components_first():
    result = compute_health_score(
        _perfect_metrics(
            monthly_expense=8000.0,  # savings rate exactly 0%
            liquid_assets=2000.0,  # 0.5 months -> score 8.3
            monthly_debt_payments=2600.0,  # 32.5% DTI -> score 13.5
        )
    )
    keys = [r["key"] for r in result["recommendations"]]
    assert keys[:3] == ["savings_rate", "emergency_fund", "debt_burden"]
    assert len(result["recommendations"]) <= 4
    assert all(r["text"] for r in result["recommendations"])


def test_grade_bands():
    assert compute_health_score(_perfect_metrics())["grade"] == "Excellent"
    low = compute_health_score(
        _perfect_metrics(
            monthly_expense=6800.0,  # 15%
            liquid_assets=8000.0,  # 2 months
            monthly_debt_payments=2000.0,  # 25% DTI
            credit_balance=14000.0,  # 70% util
            goals_avg_progress=0.4,
            budget_statuses={"on_track": 1, "at_risk": 1, "over": 1},
        )
    )
    assert low["grade"] in {"Fair", "Good"}


# ---------- endpoint integration tests ----------

async def _seed_scenario(client):
    """Create a small but realistic data set."""
    await client.post(
        f"{API}/categories", json={"name": "Salary", "type": "income"}
    )
    await client.post(
        f"{API}/categories", json={"name": "Groceries", "type": "expense"}
    )
    await client.post(
        f"{API}/accounts",
        json={"name": "Checking", "type": "checking", "opening_balance": 10000},
    )
    accounts = (await client.get(f"{API}/accounts")).json()
    checking = accounts[0]["id"]

    categories = (await client.get(f"{API}/categories")).json()
    salary = next(c for c in categories if c["name"] == "Salary")
    groceries = next(c for c in categories if c["name"] == "Groceries")

    await client.post(
        f"{API}/transactions",
        json={
            "account_id": checking,
            "category_id": salary["id"],
            "date": "2026-07-01",
            "amount": 8000,
            "description": "Salary",
        },
    )
    await client.post(
        f"{API}/transactions",
        json={
            "account_id": checking,
            "category_id": groceries["id"],
            "date": "2026-07-05",
            "amount": -400,
            "description": "Groceries",
        },
    )
    await client.post(f"{API}/debts", json={"name": "Student Loan", "type": "student", "principal": 12000, "interest_rate": 5.5, "min_payment": 150})
    await client.post(f"{API}/credit-cards", json={"name": "Chase", "balance": 500, "credit_limit": 10000, "apr": 24.99, "min_payment": 25})
    await client.post(f"{API}/savings-goals", json={"name": "Emergency Fund", "target_amount": 10000, "current_amount": 2000})


async def test_health_score_endpoint_returns_full_shape(auth_client):
    await _seed_scenario(auth_client)
    resp = await auth_client.get(f"{API}/health-score")
    assert resp.status_code == 200
    body = resp.json()
    assert 0 <= body["score"] <= 100
    assert body["grade"] in {"Excellent", "Good", "Fair", "Needs work"}
    assert body["period_label"]
    assert len(body["subscores"]) == 6
    assert sum(s["weight"] for s in body["subscores"]) == 100
    assert isinstance(body["recommendations"], list)


async def test_health_score_requires_auth(client):
    resp = await client.get(f"{API}/health-score")
    assert resp.status_code in {401, 403}


async def test_health_score_reflects_liquid_assets(auth_client):
    await _seed_scenario(auth_client)
    body = (await auth_client.get(f"{API}/health-score")).json()
    fund = next(s for s in body["subscores"] if s["key"] == "emergency_fund")
    # Liquid = $10k opening + $7.6k net transactions = $17.6k; expenses small.
    assert "months" in fund["detail"]


async def test_savings_rate_uses_positive_expense_magnitude(auth_client):
    """Regression: the router must pass expense as a positive magnitude, not the
    negative sum of transactions (which produced 'Saving 139%')."""
    await _seed_scenario(auth_client)  # income 8000, expense 400 in July
    body = (await auth_client.get(f"{API}/health-score")).json()
    savings = next(s for s in body["subscores"] if s["key"] == "savings_rate")
    # 8000 income, 400 expense -> 95% savings rate; a negative expense would
    # have produced >100% and the sub-score text would look absurd.
    assert savings["score"] == 100.0
    assert "95%" in savings["detail"]


async def test_budget_at_75pct_used_is_not_at_risk_at_month_end(auth_client):
    """Regression: on the last day of the month a budget that has used ~90% of
    its limit can no longer go over, so it must be 'on track' — not 'at risk'.
    Mid-month it should still warn."""
    from datetime import date, timedelta

    await auth_client.post(f"{API}/categories", json={"name": "Dining", "type": "expense"})
    await auth_client.post(
        f"{API}/accounts", json={"name": "Checking", "type": "checking", "opening_balance": 1000}
    )
    accounts = (await auth_client.get(f"{API}/accounts")).json()
    checking = accounts[0]["id"]
    cats = (await auth_client.get(f"{API}/categories")).json()
    dining = next(c for c in cats if c["name"] == "Dining")

    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = ((month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - month_start).days
    days_elapsed = max((today - month_start).days + 1, 1)

    await auth_client.post(
        f"{API}/budgets",
        json={"name": "Dining", "amount": 100, "period": "monthly", "category_id": dining["id"]},
    )
    await auth_client.post(
        f"{API}/transactions",
        json={"account_id": checking, "category_id": dining["id"], "date": today.isoformat(), "amount": -90, "description": "Dinner"},
    )

    body = (await auth_client.get(f"{API}/health-score")).json()
    detail = next(s for s in body["subscores"] if s["key"] == "budget_adherence")["detail"]
    if days_elapsed >= days_in_month:
        assert "on track" in detail and "at risk" not in detail
    else:
        assert "at risk" in detail


async def test_health_score_isolated_per_user(auth_client, second_user_headers):
    await _seed_scenario(auth_client)
    resp = await auth_client.get(f"{API}/health-score")
    assert resp.status_code == 200
    resp2 = await auth_client.get(f"{API}/health-score", headers=second_user_headers)
    assert resp2.status_code == 200
    # Different users can have different scores — the second user has no data.
    assert resp2.json()["recommendations"] != resp.json()["recommendations"]
