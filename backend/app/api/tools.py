"""Financial tools endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Debt
from app.models.user import User
from app.services.debt_payoff import compare_strategies
from app.services.retirement import run_projection

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
