"""Financial tools endpoints."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Debt, Investment
from app.models.finance import Account, Budget, Category, Transaction
from app.models.user import User
from app.services.budget_forecast import forecast, month_key
from app.services.debt_payoff import compare_strategies
from app.services.financial_assistant import answer_question
from app.services.retirement import run_projection
from app.services.tax_estimation import estimate_tax, suggest_loss_harvesting

router = APIRouter(prefix="/tools", tags=["tools"])

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


@router.get("/loss-harvesting")
async def loss_harvesting(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest tax-loss harvesting candidates from the user's holdings.

    Flags every investment trading below cost basis by at least $100 and
    estimates the tax saving from realizing the loss, assuming long-term
    capital gains rates.
    """
    rows = (
        await db.execute(
            select(Investment).where(Investment.user_id == current_user.id)
        )
    ).scalars().all()
    investments = [
        {
            "name": r.name,
            "symbol": r.symbol,
            "type": r.type,
            "cost_basis": float(r.cost_basis or 0),
            "current_value": float(r.current_value or 0),
        }
        for r in rows
    ]
    return {
        "candidates": suggest_loss_harvesting(investments),
        "note": "Realized losses offset capital gains first, then up to $3,000 of ordinary income per year; the remainder carries forward.",
    }


class FinancialAssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500, description="Natural-language financial question")


@router.post("/assistant")
async def financial_assistant(
    data: FinancialAssistantRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Answer a natural-language financial question using the user's data.

    The assistant parses the question to identify intent (spending, saving,
    net worth, budget, debt, investments, income, retirement, tax, or health)
    and generates a contextual response with actionable guidance.
    """
    # Fetch the user's dashboard data for context

    # Build a mock request to get dashboard data

    # We need the dashboard data, so let's fetch it directly
    today = date.today()
    month_start = today.replace(day=1)
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    from sqlalchemy import select as sqla_select

    # Get accounts
    account_rows = (
        await db.execute(
            sqla_select(Account).where(Account.user_id == current_user.id)
        )
    ).scalars().all()

    account_balances = {a.id: float(a.opening_balance or 0) for a in account_rows}
    balance_txns = (
        await db.execute(
            sqla_select(Transaction)
            .where(
                Transaction.user_id == current_user.id,
                Transaction.status != "pending",
            )
            .order_by(Transaction.date, Transaction.id)
        )
    ).scalars().all()
    for txn in balance_txns:
        account_balances[txn.account_id] = account_balances.get(txn.account_id, 0.0) + float(txn.amount)
    total_balance = sum(account_balances.values())

    # Get transactions for the month
    txn_rows = (
        await db.execute(
            sqla_select(Transaction)
            .where(
                Transaction.user_id == current_user.id,
                Transaction.date >= month_start,
                Transaction.date < next_month_start,
                Transaction.status != "pending",
            )
        )
    ).scalars().all()

    monthly_income = sum(float(t.amount) for t in txn_rows if t.amount > 0)
    monthly_expense = abs(sum(float(t.amount) for t in txn_rows if t.amount < 0))

    # Get debt
    debt_rows = (
        await db.execute(
            sqla_select(Debt).where(Debt.user_id == current_user.id, Debt.is_active.is_(True))
        )
    ).scalars().all()
    total_debt = sum(float(d.principal) for d in debt_rows)

    # Get investments
    inv_rows = (
        await db.execute(
            sqla_select(Investment).where(Investment.user_id == current_user.id)
        )
    ).scalars().all()
    investment_value = sum(float(i.current_value) for i in inv_rows)
    investment_gain_loss = sum(
        float(i.current_value) - float(i.cost_basis) for i in inv_rows
    )

    # Get budgets
    budget_rows = (
        await db.execute(
            sqla_select(Budget).where(Budget.user_id == current_user.id)
        )
    ).scalars().all()

    # Get health score
    from app.api.health import gather_health_metrics, compute_health_score as _compute_health_score
    metrics = await gather_health_metrics(db, current_user.id)
    health = _compute_health_score(metrics)

    dashboard_data = {
        "monthly": {"income": monthly_income, "expense": monthly_expense, "net": monthly_income - monthly_expense},
        "net_worth": total_balance - total_debt,
        "debt": {"total": total_debt},
        "investments": {"total_value": investment_value, "gain_loss": investment_gain_loss},
        "budgets": [
            {"status": "on_track", "name": b.name, "amount": float(b.amount)}
            for b in budget_rows
        ],
        "health": {"score": health["score"], "grade": health["grade"]},
    }

    return answer_question(data.question, dashboard_data)
