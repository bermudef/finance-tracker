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

router = APIRouter(prefix="/tools", tags=["tools"])


class DebtPayoffRequest(BaseModel):
    extra_monthly: float = Field(default=200.0, ge=0, description="Extra monthly payment on top of minimums")


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
