"""Debt payoff simulation and endpoint tests."""
from __future__ import annotations

from app.services.debt_payoff import compare_strategies, simulate_debt_payoff

API = "/api/v1"


def _debts():
    return [
        {"name": "Student Loan", "principal": 12000, "interest_rate": 5.5, "min_payment": 150},
        {"name": "Car", "principal": 8000, "interest_rate": 3.9, "min_payment": 250},
        {"name": "Credit Card", "principal": 2400, "interest_rate": 24.99, "min_payment": 85},
    ]


def test_zero_interest_pays_off_in_known_months():
    debts = [
        {"name": "A", "principal": 1000, "interest_rate": 0, "min_payment": 100},
        {"name": "B", "principal": 100, "interest_rate": 0, "min_payment": 25},
    ]
    result = simulate_debt_payoff(debts, extra_monthly=100, strategy="avalanche")
    assert result["total_interest"] == 0.0
    assert result["did_not_converge"] is False
    assert result["months_to_debt_free"] is not None
    # Timeline starts at the full balance and ends at 0.
    assert result["timeline"][0]["remaining"] == 1100.0
    assert result["timeline"][-1]["remaining"] == 0.0


def test_avalanche_targets_highest_apr_first():
    debts = [
        {"name": "Low APR", "principal": 3000, "interest_rate": 5.0, "min_payment": 100},
        {"name": "High APR", "principal": 500, "interest_rate": 24.0, "min_payment": 40},
    ]
    result = simulate_debt_payoff(debts, extra_monthly=100, strategy="avalanche")
    assert result["payoff_order"][0]["name"] == "High APR"


def test_snowball_targets_lowest_balance_first():
    debts = [
        {"name": "Big", "principal": 5000, "interest_rate": 5.0, "min_payment": 150},
        {"name": "Small", "principal": 300, "interest_rate": 12.0, "min_payment": 40},
    ]
    result = simulate_debt_payoff(debts, extra_monthly=100, strategy="snowball")
    assert result["payoff_order"][0]["name"] == "Small"


def test_avalanche_wins_on_interest():
    """Avalanche minimizes total interest; snowball is never strictly better."""
    debts = [
        {"name": "Low APR", "principal": 8000, "interest_rate": 4.0, "min_payment": 200},
        {"name": "High APR", "principal": 2000, "interest_rate": 22.0, "min_payment": 60},
    ]
    ava = simulate_debt_payoff(debts, extra_monthly=150, strategy="avalanche")
    snow = simulate_debt_payoff(debts, extra_monthly=150, strategy="snowball")
    assert not ava["did_not_converge"] and not snow["did_not_converge"]
    assert ava["total_interest"] <= snow["total_interest"]
    comparison = compare_strategies(debts, 150)
    assert comparison["interest_savings"] == round(snow["total_interest"] - ava["total_interest"], 2)


def test_extra_payment_accelerates_payoff():
    debts = _debts()
    base = simulate_debt_payoff(debts, extra_monthly=0, strategy="avalanche")
    accelerated = simulate_debt_payoff(debts, extra_monthly=500, strategy="avalanche")
    assert accelerated["months_to_debt_free"] < base["months_to_debt_free"]
    assert accelerated["total_interest"] < base["total_interest"]


def test_ignores_zero_principal_debts():
    debts = [
        {"name": "Paid Off", "principal": 0, "interest_rate": 9.0, "min_payment": 50},
        {"name": "Real", "principal": 1000, "interest_rate": 6.0, "min_payment": 100},
    ]
    result = simulate_debt_payoff(debts, extra_monthly=50, strategy="avalanche")
    assert "Paid Off" not in [p["name"] for p in result["payoff_order"]]
    assert result["timeline"][0]["remaining"] == 1000.0


def test_default_minimum_floor_for_missing_min_payment():
    debts = [{"name": "Card", "principal": 500, "interest_rate": 18.0, "min_payment": None}]
    result = simulate_debt_payoff(debts, extra_monthly=0, strategy="avalanche")
    assert result["did_not_converge"] is False
    assert result["months_to_debt_free"] is not None


# ---- endpoint tests ----


async def test_debt_payoff_requires_auth(client):
    resp = await client.post(f"{API}/tools/debt-payoff", json={"extra_monthly": 200})
    assert resp.status_code == 401


async def test_debt_payoff_empty_state(auth_client):
    resp = await auth_client.post(f"{API}/tools/debt-payoff", json={"extra_monthly": 200})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_principal"] == 0.0
    assert body["debt_count"] == 0
    assert body["avalanche"]["months_to_debt_free"] == 0


async def test_debt_payoff_uses_only_users_debts(auth_client, second_user_headers):
    await auth_client.post(
        f"{API}/debts",
        json={"name": "My Loan", "type": "student", "principal": 10000,
              "interest_rate": 6.0, "min_payment": 200},
    )
    mine = await auth_client.post(
        f"{API}/tools/debt-payoff", json={"extra_monthly": 300}
    )
    assert mine.json()["total_principal"] == 10000.0

    other = await auth_client.post(
        f"{API}/tools/debt-payoff",
        headers=second_user_headers,
        json={"extra_monthly": 300},
    )
    assert other.json()["total_principal"] == 0.0
    assert other.json()["debt_count"] == 0


async def test_debt_payoff_inactive_debts_excluded(auth_client):
    created = await auth_client.post(
        f"{API}/debts",
        json={"name": "Sold Car", "type": "auto", "principal": 15000,
              "interest_rate": 4.5, "min_payment": 400},
    )
    await auth_client.put(f"{API}/debts/{created.json()['id']}", json={"is_active": False})
    resp = await auth_client.post(f"{API}/tools/debt-payoff", json={"extra_monthly": 100})
    assert resp.json()["total_principal"] == 0.0


async def test_debt_payoff_full_simulation(auth_client):
    await auth_client.post(
        f"{API}/debts",
        json={"name": "Student Loan", "type": "student", "principal": 12000,
              "interest_rate": 5.5, "min_payment": 150},
    )
    await auth_client.post(
        f"{API}/debts",
        json={"name": "Credit Card", "type": "credit_card", "principal": 2400,
              "interest_rate": 24.99, "min_payment": 85},
    )
    body = (await auth_client.post(
        f"{API}/tools/debt-payoff", json={"extra_monthly": 200}
    )).json()

    assert body["total_principal"] == 14400.0
    assert body["debt_count"] == 2
    for strategy in ("avalanche", "snowball"):
        sim = body[strategy]
        assert sim["did_not_converge"] is False
        assert sim["months_to_debt_free"] > 0
        assert sim["timeline"][0]["remaining"] == 14400.0
        assert sim["timeline"][-1]["remaining"] == 0.0
        assert {p["name"] for p in sim["payoff_order"]} == {"Student Loan", "Credit Card"}
    # Avalanche pays the 24.99% card first.
    assert body["avalanche"]["payoff_order"][0]["name"] == "Credit Card"
    # Extra monthly payment is clamped to non-negative.
    bad = await auth_client.post(f"{API}/tools/debt-payoff", json={"extra_monthly": -5})
    assert bad.status_code == 422


# ---- retirement projection tests ----


async def test_retirement_projection_requires_auth(client):
    resp = await client.post(f"{API}/tools/retirement-projection", json={
        "current_age": 30, "retirement_age": 65,
    })
    assert resp.status_code == 401


async def test_retirement_projection_structure(auth_client):
    resp = await auth_client.post(f"{API}/tools/retirement-projection", json={
        "current_age": 30,
        "retirement_age": 65,
        "current_balance": 50000,
        "monthly_contribution": 1000,
        "expected_return": 7.0,
        "inflation_rate": 2.5,
        "std_dev": 12.0,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["years_to_retirement"] == 35
    assert len(body["series"]) == 35
    assert "summary" in body
    first = body["series"][0]
    assert {"age", "p10", "p25", "median", "p75", "p90"} <= set(first.keys())
    # Percentile ordering must hold at every year.
    for pt in body["series"]:
        assert pt["p10"] <= pt["p25"] <= pt["median"] <= pt["p75"] <= pt["p90"]


async def test_retirement_projection_is_deterministic(auth_client):
    """Identical inputs must produce identical outputs (deterministic seed)."""
    body1 = (await auth_client.post(
        f"{API}/tools/retirement-projection",
        json={"current_age": 30, "retirement_age": 65, "current_balance": 50000,
              "monthly_contribution": 1000, "expected_return": 7.0,
              "inflation_rate": 2.5, "std_dev": 12.0},
    )).json()
    body2 = (await auth_client.post(
        f"{API}/tools/retirement-projection",
        json={"current_age": 30, "retirement_age": 65, "current_balance": 50000,
              "monthly_contribution": 1000, "expected_return": 7.0,
              "inflation_rate": 2.5, "std_dev": 12.0},
    )).json()
    assert body1["series"] == body2["series"]


async def test_retirement_projection_zero_years(auth_client):
    resp = await auth_client.post(f"{API}/tools/retirement-projection", json={
        "current_age": 65, "retirement_age": 65, "current_balance": 100000,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["years_to_retirement"] == 0
    assert body["series"] == []
    assert body["summary"]["median_nominal"] == 100000.0


async def test_retirement_projection_input_validation(auth_client):
    # current_age below minimum
    bad = await auth_client.post(f"{API}/tools/retirement-projection", json={
        "current_age": 17, "retirement_age": 65,
    })
    assert bad.status_code == 422
    # retirement_age below minimum
    bad = await auth_client.post(f"{API}/tools/retirement-projection", json={
        "current_age": 30, "retirement_age": 17,
    })
    assert bad.status_code == 422


# ---- budget forecast tests ----


async def test_budget_forecast_requires_auth(client):
    resp = await client.post(f"{API}/tools/budget-forecast", json={"months_back": 6})
    assert resp.status_code == 401


async def test_budget_forecast_structure(auth_client):
    """Forecast returns forecasts list with expected keys."""
    resp = await auth_client.post(f"{API}/tools/budget-forecast", json={"months_back": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert "forecasts" in body
    assert "flagged" in body
    assert "total_forecast" in body
    assert "total_budget" in body
    if body["forecasts"]:
        f = body["forecasts"][0]
        assert {"category", "predicted", "p10", "p90", "budget", "will_exceed", "confidence", "months_of_data"} <= set(f.keys())


async def test_budget_forecast_empty_state(auth_client):
    """With no budgets or transactions, forecast returns empty lists."""
    resp = await auth_client.post(f"{API}/tools/budget-forecast", json={"months_back": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["forecasts"] == []
    assert body["flagged"] == []
    assert body["total_forecast"] == 0.0
    assert body["total_budget"] == 0.0


# ---- tax estimation tests ----


async def test_tax_estimate_requires_auth(client):
    resp = await client.post(f"{API}/tools/tax-estimate", json={"annual_income": 100000})
    assert resp.status_code == 401


async def test_tax_estimate_structure(auth_client):
    resp = await auth_client.post(
        f"{API}/tools/tax-estimate",
        json={"annual_income": 100000, "capital_gains": 5000, "deductions": 5000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "annual_income" in body
    assert "taxable_income" in body
    assert "ordinary_tax" in body
    assert "capital_gains_tax" in body
    assert "total_tax" in body
    assert "effective_rate" in body
    assert "marginal_rate" in body
    assert "quarterly_estimated" in body
    assert body["total_tax"] >= 0


async def test_tax_estimate_zero_income(auth_client):
    resp = await auth_client.post(f"{API}/tools/tax-estimate", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tax"] == 0.0
    assert body["effective_rate"] == 0.0


async def test_tax_estimate_high_income(auth_client):
    """High income should have a higher effective rate."""
    low = (
        await auth_client.post(
            f"{API}/tools/tax-estimate",
            json={"annual_income": 50000},
        )
    ).json()
    high = (
        await auth_client.post(
            f"{API}/tools/tax-estimate",
            json={"annual_income": 200000},
        )
    ).json()
    assert high["effective_rate"] > low["effective_rate"]


# ---- financial assistant tests ----


async def test_assistant_requires_auth(client):
    resp = await client.post(f"{API}/tools/assistant", json={"question": "Where is my money going?"})
    assert resp.status_code == 401


async def test_assistant_structure(auth_client):
    resp = await auth_client.post(
        f"{API}/tools/assistant",
        json={"question": "Where is my money going?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "intent" in body
    assert "question" in body
    assert "answer" in body
    assert isinstance(body["answer"], str)
    assert len(body["answer"]) > 0


async def test_assistant_unknown_intent(auth_client):
    resp = await auth_client.post(
        f"{API}/tools/assistant",
        json={"question": "What is the weather today?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent"] == "unknown"
    assert "spending" in body["answer"].lower() or "savings" in body["answer"].lower()
