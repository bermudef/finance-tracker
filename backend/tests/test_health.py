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


def test_debt_burden_status_follows_dti_bands():
    on_track = compute_health_score(_perfect_metrics(monthly_debt_payments=1200.0))  # 15%
    debt = next(s for s in on_track["subscores"] if s["key"] == "debt_burden")
    assert debt["status"] == "on_track"

    at_risk = compute_health_score(_perfect_metrics(monthly_debt_payments=2080.0))  # 26%
    debt = next(s for s in at_risk["subscores"] if s["key"] == "debt_burden")
    assert debt["status"] == "at_risk"

    over = compute_health_score(_perfect_metrics(monthly_debt_payments=3200.0))  # 40%
    debt = next(s for s in over["subscores"] if s["key"] == "debt_burden")
    assert debt["status"] == "over"


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


def test_cards_without_limits_are_neutral_not_zero():
    """Regression: a card with no reported limit is a data gap, not a 0-score."""
    result = compute_health_score(
        _perfect_metrics(credit_balance=500.0, credit_limit=0.0, credit_cards_count=2)
    )
    credit = next(s for s in result["subscores"] if s["key"] == "credit_utilization")
    assert credit["score"] == 50.0
    assert "no reported limits" in credit["detail"]


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


def test_savings_rate_over_75_is_on_track():
    """Savings rate must score strictly over 75 to be 'on track' (no
    recommendation). 15% saved scores 75 -> still flagged; 16% scores 80 -> ok."""
    at_threshold = compute_health_score(_perfect_metrics(monthly_expense=6800.0))  # 15% saved
    assert "savings_rate" in [r["key"] for r in at_threshold["recommendations"]]
    above = compute_health_score(_perfect_metrics(monthly_expense=6720.0))  # 16% saved
    assert "savings_rate" not in [r["key"] for r in above["recommendations"]]


def test_credit_utilization_status_follows_utilization_bands():
    """Credit utilization status is judged on the utilization ratio, not the
    normalized score (which is already 100 for anything at/under 30%):
        < 25%  -> on track
        25-30% -> at risk
        > 30%  -> over
    """
    on_track = compute_health_score(
        _perfect_metrics(credit_balance=4800.0, credit_limit=20000.0)  # 24% -> on track
    )
    credit = next(s for s in on_track["subscores"] if s["key"] == "credit_utilization")
    assert credit["status"] == "on_track"
    assert "credit_utilization" not in [r["key"] for r in on_track["recommendations"]]

    at_risk = compute_health_score(
        _perfect_metrics(credit_balance=5200.0, credit_limit=20000.0)  # 26% -> at risk
    )
    credit = next(s for s in at_risk["subscores"] if s["key"] == "credit_utilization")
    assert credit["status"] == "at_risk"
    assert credit["score"] == 100.0  # score still reads perfect at 26%
    assert "credit_utilization" in [r["key"] for r in at_risk["recommendations"]]

    boundary = compute_health_score(
        _perfect_metrics(credit_balance=6000.0, credit_limit=20000.0)  # exactly 30% -> at risk
    )
    credit = next(s for s in boundary["subscores"] if s["key"] == "credit_utilization")
    assert credit["status"] == "at_risk"

    over = compute_health_score(
        _perfect_metrics(credit_balance=6400.0, credit_limit=20000.0)  # 32% -> over
    )
    credit = next(s for s in over["subscores"] if s["key"] == "credit_utilization")
    assert credit["status"] == "over"
    assert "credit_utilization" in [r["key"] for r in over["recommendations"]]


def test_credit_utilization_over_75_is_on_track():
    """Credit utilization must score strictly over 75 to be 'on track'. 37.5%
    utilization scores exactly 75 -> still flagged; 25% scores 100 -> ok."""
    at_boundary = compute_health_score(
        _perfect_metrics(credit_balance=7500.0, credit_limit=20000.0)  # 37.5% -> score 75
    )
    assert "credit_utilization" in [r["key"] for r in at_boundary["recommendations"]]
    under_util = compute_health_score(
        _perfect_metrics(credit_balance=4000.0, credit_limit=20000.0)  # 20% -> on track
    )
    assert "credit_utilization" not in [r["key"] for r in under_util["recommendations"]]


def test_emergency_fund_over_75_is_on_track():
    """Emergency fund must score strictly over 75 to be 'on track'. 4.5 months
    scores exactly 75 -> still flagged; 5 months scores ~83 -> ok."""
    at_boundary = compute_health_score(
        _perfect_metrics(liquid_assets=18000.0)  # 4.5 months -> score 75
    )
    assert "emergency_fund" in [r["key"] for r in at_boundary["recommendations"]]
    funded = compute_health_score(
        _perfect_metrics(liquid_assets=20000.0)  # 5 months -> score ~83
    )
    assert "emergency_fund" not in [r["key"] for r in funded["recommendations"]]


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
    """Create a small but realistic data set.

    Dates are derived from date.today() so the fixtures always land inside the
    month the health endpoint is measuring (regardless of when the suite runs):
    salary on the 1st, groceries today.
    """
    from datetime import date

    today = date.today()
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
            "date": today.replace(day=1).isoformat(),
            "amount": 8000,
            "description": "Salary",
        },
    )
    await client.post(
        f"{API}/transactions",
        json={
            "account_id": checking,
            "category_id": groceries["id"],
            "date": today.isoformat(),
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


async def test_budget_status_driven_by_actual_spend(auth_client):
    """Regression: status is judged by actual spend against the limit, not by a
    linear projection. A budget under its limit is 'on track' even if the
    projection suggests an overrun; once spend reaches/exceeds the limit it is
    'at risk' regardless of the date. The app clock is frozen so the test is
    deterministic on any date."""
    from datetime import date
    from unittest.mock import patch

    class _FrozenDate(date):
        """A datetime.date subclass whose today() returns a fixed value; all
        arithmetic (replace, timedelta) works natively because it IS a date."""

        _fixed: date | None = None

        @classmethod
        def today(cls):
            return cls._fixed

    await auth_client.post(f"{API}/categories", json={"name": "Dining", "type": "expense"})
    await auth_client.post(
        f"{API}/accounts", json={"name": "Checking", "type": "checking", "opening_balance": 1000}
    )
    accounts = (await auth_client.get(f"{API}/accounts")).json()
    checking = accounts[0]["id"]
    cats = (await auth_client.get(f"{API}/categories")).json()
    dining = next(c for c in cats if c["name"] == "Dining")

    await auth_client.post(
        f"{API}/budgets",
        json={"name": "Dining", "amount": 100, "period": "monthly", "category_id": dining["id"]},
    )
    # Transaction dated on the 1st, well inside the frozen month: 90% of the
    # budget spent, but still under the limit, so it must stay 'on track'.
    await auth_client.post(
        f"{API}/transactions",
        json={"account_id": checking, "category_id": dining["id"], "date": "2026-08-01",
              "amount": -90, "description": "Dinner"},
    )

    # (frozen today, expected detail fragment, unexpected fragment)
    cases = [
        (date(2026, 8, 15), "on track", "at risk"),  # under limit: on track, not at risk
        (date(2026, 8, 31), "on track", "at risk"),  # last day: still under limit
    ]
    for frozen_today, expected, unexpected in cases:
        _FrozenDate._fixed = frozen_today
        with patch("app.api.health.date", _FrozenDate):
            body = (await auth_client.get(f"{API}/health-score")).json()
        detail = next(s for s in body["subscores"] if s["key"] == "budget_adherence")["detail"]
        assert expected in detail, f"on {frozen_today}: {detail!r} should contain {expected!r}"
        assert unexpected not in detail, f"on {frozen_today}: {detail!r} should not contain {unexpected!r}"

    # Once spend reaches the limit, the budget is 'at risk' on any date.
    await auth_client.post(
        f"{API}/transactions",
        json={"account_id": checking, "category_id": dining["id"], "date": "2026-08-05",
              "amount": -15, "description": "More dinner"},
    )
    _FrozenDate._fixed = date(2026, 8, 31)
    with patch("app.api.health.date", _FrozenDate):
        body = (await auth_client.get(f"{API}/health-score")).json()
    detail = next(s for s in body["subscores"] if s["key"] == "budget_adherence")["detail"]
    assert "at risk" in detail, f"over-limit budget should be at risk: {detail!r}"


async def test_health_score_isolated_per_user(auth_client, second_user_headers):
    await _seed_scenario(auth_client)
    resp = await auth_client.get(f"{API}/health-score")
    assert resp.status_code == 200
    resp2 = await auth_client.get(f"{API}/health-score", headers=second_user_headers)
    assert resp2.status_code == 200
    # Different users can have different scores — the second user has no data.
    assert resp2.json()["recommendations"] != resp.json()["recommendations"]


async def test_inactive_credit_cards_excluded_from_health(auth_client):
    """Regression: a deactivated card must not drag down credit utilization,
    debt burden, or the card count."""
    card = await auth_client.post(
        f"{API}/credit-cards",
        json={"name": "Old Card", "balance": 9000, "credit_limit": 10000, "apr": 20,
              "min_payment": 250},
    )
    await auth_client.put(
        f"{API}/credit-cards/{card.json()['id']}", json={"is_active": False}
    )
    body = (await auth_client.get(f"{API}/health-score")).json()
    credit = next(s for s in body["subscores"] if s["key"] == "credit_utilization")
    debt = next(s for s in body["subscores"] if s["key"] == "debt_burden")
    # No active cards -> neutral credit score, no debt payments recorded.
    assert credit["score"] == 70.0
    assert debt["detail"] == "No income to measure debt load against"


async def test_emergency_fund_not_inflated_for_new_users(auth_client):
    """Regression: the 3-month expense average must not be diluted by empty
    months for a user with only one month of history (previously inflated the
    emergency-fund score ~3x)."""
    from datetime import date

    today = date.today()
    await auth_client.post(f"{API}/categories", json={"name": "Salary", "type": "income"})
    await auth_client.post(f"{API}/categories", json={"name": "Rent", "type": "expense"})
    await auth_client.post(
        f"{API}/accounts", json={"name": "Checking", "type": "checking", "opening_balance": 0}
    )
    accounts = (await auth_client.get(f"{API}/accounts")).json()
    checking = accounts[0]["id"]
    cats = (await auth_client.get(f"{API}/categories")).json()
    rent = next(c for c in cats if c["name"] == "Rent")

    # Current + previous month both have spending so the average is not diluted.
    for offset_months in (1, 0):
        year = today.year
        month = today.month - offset_months
        while month < 1:
            month += 12
            year -= 1
        await auth_client.post(
            f"{API}/transactions",
            json={"account_id": checking, "category_id": rent["id"],
                  "date": f"{year}-{month:02d}-01", "amount": -500.0, "description": "Rent"},
        )

    body = (await auth_client.get(f"{API}/health-score")).json()
    fund = next(s for s in body["subscores"] if s["key"] == "emergency_fund")
    # ~$1000 average expense; with no liquid assets the fund cannot be 100.
    assert fund["score"] == 0.0  # no assets -> nothing covered


async def test_inactive_credit_cards_excluded_from_dashboard_net_worth(auth_client):
    """Regression: inactive cards and debts must not count toward net worth."""
    await auth_client.post(
        f"{API}/accounts", json={"name": "Checking", "type": "checking", "opening_balance": 5000}
    )
    card = await auth_client.post(
        f"{API}/credit-cards", json={"name": "Closed Visa", "balance": 3000, "credit_limit": 5000, "apr": 20}
    )
    debt = await auth_client.post(
        f"{API}/debts", json={"name": "Sold Car", "type": "auto", "principal": 8000, "interest_rate": 4}
    )
    await auth_client.put(f"{API}/credit-cards/{card.json()['id']}", json={"is_active": False})
    await auth_client.put(f"{API}/debts/{debt.json()['id']}", json={"is_active": False})

    body = (await auth_client.get(f"{API}/dashboard")).json()
    assert body["net_worth"] == 5000.0  # only the checking balance remains
    assert body["debt"]["total"] == 0.0


async def test_health_score_excludes_pending_transactions(auth_client):
    from datetime import date

    await auth_client.post(f"{API}/categories", json={"name": "Salary", "type": "income"})
    await auth_client.post(f"{API}/categories", json={"name": "Groceries", "type": "expense"})
    await auth_client.post(
        f"{API}/accounts", json={"name": "Checking", "type": "checking", "opening_balance": 0}
    )
    accounts = (await auth_client.get(f"{API}/accounts")).json()
    checking = accounts[0]["id"]
    cats = (await auth_client.get(f"{API}/categories")).json()
    salary = next(c for c in cats if c["name"] == "Salary")
    groceries = next(c for c in cats if c["name"] == "Groceries")
    await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": checking,
            "category_id": salary["id"],
            "date": date.today().isoformat(),
            "amount": 8000.0,
            "description": "Posted salary",
            "status": "posted",
        },
    )
    await auth_client.post(
        f"{API}/transactions",
        json={
            "account_id": checking,
            "category_id": groceries["id"],
            "date": date.today().isoformat(),
            "amount": -400.0,
            "description": "Pending groceries",
            "status": "pending",
        },
    )
    body = (await auth_client.get(f"{API}/health-score")).json()
    savings = next(s for s in body["subscores"] if s["key"] == "savings_rate")
    assert "100%" in savings["detail"]
