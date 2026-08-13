"""Financial health score endpoint.

Gathers the raw metrics for the current month and hands them to the pure
`compute_health_score` service, so the scoring rules live in exactly one place
and can be unit tested without a database.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import CreditCard, Debt, SavingsGoal
from app.models.finance import Account, Transaction
from app.models.user import User
from app.services.health_score import compute_health_score

router = APIRouter(prefix="/health-score", tags=["health"])

# Account types that count as "liquid" (available for emergencies). Investment
# accounts live in a separate table, so bank accounts here are cash-like by
# definition; credit-type accounts are excluded.
LIQUID_ACCOUNT_TYPES = {"checking", "savings", "cash"}


async def _sum_transactions(
    db: AsyncSession, user_id: int, start: date, end: date, positive: bool
) -> float:
    query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.date >= start,
        Transaction.date < end,
        Transaction.user_id == user_id,
    )
    query = query.where(Transaction.amount > 0) if positive else query.where(Transaction.amount < 0)
    return float((await db.execute(query)).scalar() or 0)


async def gather_health_metrics(db: AsyncSession, user_id: int) -> dict:
    """Collect every raw signal the health score needs for `user_id`.

    Exported so the dashboard can show a health summary without duplicating
    the query logic.
    """
    today = date.today()
    month_start = today.replace(day=1)
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    # --- Cash flow ---
    income_this_month = await _sum_transactions(db, user_id, month_start, next_month_start, positive=True)
    # _sum_transactions(positive=False) returns the negative sum; the service
    # expects positive magnitudes (savings rate = (income - expense) / income).
    expense_this_month = -await _sum_transactions(db, user_id, month_start, next_month_start, positive=False)

    # Average monthly expense across the current + previous 2 months. Only
    # months with actual spending count toward the average: a brand-new user
    # with a single month of history must not be diluted by two empty months,
    # which would understate expenses and inflate their emergency-fund score.
    expense_sums = []
    start = month_start
    for _ in range(3):
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_expense = -await _sum_transactions(db, user_id, start, end, positive=False)
        if month_expense > 0:
            expense_sums.append(month_expense)
        start = (start - timedelta(days=1)).replace(day=1)
    avg_monthly_expense = sum(expense_sums) / len(expense_sums) if expense_sums else 0.0

    # --- Liquid assets (bank accounts net of transactions) ---
    account_rows = (
        await db.execute(select(Account).where(Account.user_id == user_id))
    ).scalars().all()
    liquid_assets = 0.0
    for a in account_rows:
        if a.type not in LIQUID_ACCOUNT_TYPES:
            continue
        tx_sum = (
            await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.account_id == a.id
                )
            )
        ).scalar()
        liquid_assets += float(a.opening_balance or 0) + float(tx_sum or 0)

    # --- Debt load: minimum payments (debts + credit cards) ---
    debt_rows = (
        await db.execute(select(Debt).where(Debt.user_id == user_id, Debt.is_active.is_(True)))
    ).scalars().all()
    card_rows = (
        await db.execute(
            select(CreditCard).where(
                CreditCard.user_id == user_id, CreditCard.is_active.is_(True)
            )
        )
    ).scalars().all()
    monthly_debt_payments = sum(
        float(d.min_payment or 0) for d in debt_rows
    ) + sum(float(c.min_payment or 0) for c in card_rows)
    credit_balance = sum(float(c.balance or 0) for c in card_rows)
    credit_limit = sum(float(c.credit_limit or 0) for c in card_rows)

    # --- Budget adherence (same projected-status logic as the dashboard) ---
    from app.services.budget_status import compute_budget_statuses

    budget_list = await compute_budget_statuses(db, user_id, today)
    statuses = {"on_track": 0, "at_risk": 0, "over": 0}
    for b in budget_list:
        statuses[b["status"]] += 1

    # --- Savings goals ---
    goal_rows = (
        await db.execute(
            select(SavingsGoal).where(SavingsGoal.user_id == user_id, SavingsGoal.is_active.is_(True))
        )
    ).scalars().all()
    goal_progresses = []
    for g in goal_rows:
        target = float(g.target_amount or 0)
        current = float(g.current_amount or 0)
        if target > 0:
            goal_progresses.append(current / target)
    goals_avg_progress = sum(goal_progresses) / len(goal_progresses) if goal_progresses else None

    return {
        "monthly_income": round(income_this_month, 2),
        "monthly_expense": round(expense_this_month, 2),
        "avg_monthly_expense": round(avg_monthly_expense, 2),
        "liquid_assets": round(liquid_assets, 2),
        "monthly_debt_payments": round(monthly_debt_payments, 2),
        "budget_statuses": statuses,
        "credit_balance": round(credit_balance, 2),
        "credit_limit": round(credit_limit, 2),
        "credit_cards_count": len(card_rows),
        "goals_avg_progress": goals_avg_progress,
        "goals_count": len(goal_rows),
        "as_of": today.isoformat(),
        "period_label": month_start.strftime("%B %Y"),
    }


@router.get("")
async def get_health_score(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    metrics = await gather_health_metrics(db, current_user.id)
    return compute_health_score(metrics)
