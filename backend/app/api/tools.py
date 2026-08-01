"""Financial tools endpoints."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Debt
from app.models.finance import Budget, Category, Transaction
from app.models.user import User
from app.services.budget_forecast import forecast, month_key
from app.services.debt_payoff import compare_strategies
from app.services.retirement import run_projection
from app.services.tax_estimation import estimate_tax

router = APIRouter(prefix="/tools", tags=["tools"])


class DebtPayoffRequest(BaseModel):
    extra_monthly: float = Field(default=200.0, ge=0, description="Extra monthly payment on top of minimums")


class RetirementProjectionRequest(BaseModel):
    model_config = {"populate_by_name": True}

    current_age: int = Field(ge=18, le=100, alias="currentAge", description="Current age")
    retirement_age: int = Field(ge=18, le=100, alias="retirementAge", description="Target retirement age")
    current_balance: float = Field(default=0.0, ge=0, alias="currentBalance", description="Current retirement balance")
    monthly_contribution: float = Field(default=0.0, ge=0, alias="monthlyContribution", description="Monthly contribution")
    expected_return: float = Field(default=7.0, ge=-10, le=30, alias="expectedReturn", description="Expected annual return (%)")
    inflation_rate: float = Field(default=2.5, ge=-5, le=20, alias="inflationRate", description="Inflation rate (%)")
    std_dev: float = Field(default=12.0, ge=0, le=50, alias="stdDev", description="Annualized volatility (%)")


@router.post("/debt-payoff")
async def debt_payoff(
    data: DebtPayoffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Simulate avalanche vs. snowball payoff plans for the user's active debts.

    The simulation lives server-side so the math is consistent and testable;
    the client only supplies how much extra it wants to throw at the debt each
    month.
    """
    debt_rows = (
        await db.execute(
            select(Debt).where(
                Debt.user_id == current_user.id,
                Debt.is_active.is_(True),
                Debt.principal > 0,
            )
        )
    ).scalars().all()

    debts = [
        {
            "name": d.name,
            "principal": float(d.principal),
            "interest_rate": float(d.interest_rate or 0),
            "min_payment": float(d.min_payment) if d.min_payment else None,
        }
        for d in debt_rows
    ]

    result = compare_strategies(debts, data.extra_monthly)
    return {
        "extra_monthly": data.extra_monthly,
        "total_principal": round(sum(float(d["principal"]) for d in debts), 2),
        "debt_count": len(debts),
        **result,
    }


@router.post("/retirement-projection")
async def retirement_projection(
    data: RetirementProjectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Monte Carlo retirement projection with 2,000 simulation paths.

    Returns annual percentiles (p10 / p25 / median / p75 / p90) so the
    frontend can render a confidence band.  The simulation is deterministic
    for a given set of inputs, making it reproducible and fully testable.
    """
    return run_projection(
        current_age=data.current_age,
        retirement_age=data.retirement_age,
        current_balance=data.current_balance,
        monthly_contribution=data.monthly_contribution,
        expected_return=data.expected_return,
        inflation_rate=data.inflation_rate,
        std_dev=data.std_dev,
    )


class BudgetForecastRequest(BaseModel):
    months_back: int = Field(default=6, ge=3, le=12, description="Number of past months to analyze")


@router.post("/budget-forecast")
async def budget_forecast(
    data: BudgetForecastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast next month's spending by category using a weighted moving average.

    Analyzes the last N months of transaction history, compares against
    the user's budgets, and flags categories likely to exceed their limit.
    """
    today = date.today()
    month_starts = []
    for i in range(data.months_back):
        ms = today.replace(day=1)
        # Go back i months
        year = ms.year
        month = ms.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_starts.append(date(year, month, 1))

    # Fetch user's budgets
    budget_rows = (
        await db.execute(
            select(Budget).where(Budget.user_id == current_user.id)
        )
    ).scalars().all()

    budgets: dict[str, float] = {}
    budget_category_ids: set[int] = set()
    for b in budget_rows:
        budgets[b.category_id] = float(b.amount)
        budget_category_ids.add(b.category_id)

    # Fetch category names for the budgeted categories
    cat_rows = (
        await db.execute(
            select(Category).where(Category.id.in_(budget_category_ids))
        )
    ).scalars().all()
    cat_id_to_name = {c.id: c.name for c in cat_rows}

    # Fetch transactions for the analyzed months
    oldest_month = min(month_starts)

    txn_rows = (
        await db.execute(
            select(Transaction)
            .where(
                Transaction.user_id == current_user.id,
                Transaction.date >= oldest_month,
                Transaction.date <= today,
            )
            .order_by(Transaction.date)
        )
    ).scalars().all()

    # Aggregate spending by category for each month
    monthly_spending: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for txn in txn_rows:
        mk = month_key(txn.date)
        cat_name = cat_id_to_name.get(txn.category_id, "Uncategorized")
        monthly_spending[cat_name][mk] += float(txn.amount)

    # Build forecast input
    forecast_input = {}
    for cat_name, spending_by_month in monthly_spending.items():
        forecast_input[cat_name] = dict(spending_by_month)

    # Build budget input (map category name to budget amount)
    budget_input: dict[str, float] = {}
    for cat_id, amount in budgets.items():
        cat_name = cat_id_to_name.get(cat_id)
        if cat_name:
            budget_input[cat_name] = amount

    result = forecast(forecast_input, budget_input)
    return result


class TaxEstimateRequest(BaseModel):
    annual_income: float = Field(default=0.0, ge=0, description="Annual ordinary income")
    capital_gains: float = Field(default=0.0, ge=0, description="Long-term capital gains")
    deductions: float = Field(default=0.0, ge=0, description="Above-the-line deductions")
    self_employment_income: float = Field(default=0.0, ge=0, description="Net self-employment earnings")


@router.post("/tax-estimate")
async def tax_estimate(
    data: TaxEstimateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Estimate annual federal tax liability using 2025 brackets.

    Computes ordinary income tax, long-term capital gains tax,
    and self-employment tax. Returns a breakdown with effective
    and marginal rates plus quarterly estimated payment amounts.
    """
    return estimate_tax(
        annual_income=data.annual_income,
        capital_gains=data.capital_gains,
        deductions=data.deductions,
        self_employment_income=data.self_employment_income,
    )
