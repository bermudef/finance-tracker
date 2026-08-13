"""Budget status computation shared by the dashboard, notifications generator,
and financial health score so every surface agrees on what "on track", "at
risk", and "over" mean for a budget.

This lives in a service module (not the dashboard router) to avoid a circular
import: the dashboard depends on `gather_health_metrics` while the health score
consumes these statuses.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Budget, Transaction


async def _spent_for_budget(
    db: AsyncSession,
    user_id: int,
    category_id: Optional[int],
    period_start: date,
    period_end: date,
) -> float:
    """Total expense spend in [period_start, period_end) for a budget's scope.

    A budget without a category is a general budget and tracks every expense
    for the period; otherwise only transactions in that category count.
    """
    query = select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
        Transaction.date >= period_start,
        Transaction.date < period_end,
        Transaction.amount < 0,
        Transaction.user_id == user_id,
    )
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    return float((await db.execute(query)).scalar())


async def _expense_transaction_count(
    db: AsyncSession,
    user_id: int,
    category_id: Optional[int],
    period_start: date,
    period_end: date,
) -> int:
    """Count expense transactions for a budget scope during the month.

    A single fixed monthly payment (like rent) should not be projected as if it
    repeats every day of the month; when there is only one expense recorded, we
    treat the current spend as the budgeted run-rate for the month.
    """
    query = select(func.count(Transaction.id)).where(
        Transaction.date >= period_start,
        Transaction.date < period_end,
        Transaction.amount < 0,
        Transaction.user_id == user_id,
    )
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    return int((await db.execute(query)).scalar() or 0)


async def compute_budget_statuses(
    db: AsyncSession, user_id: int, today: Optional[date] = None
) -> list[dict]:
    """Budget list with spent/projected/status for the month containing ``today``.

    Budgets with ``rollover`` enabled carry last month's unused amount into
    the current month: the effective limit becomes amount + carryover, and
    the spend/status calculations run against that larger limit.

    Returns a list of budget dicts (id, name, amount, status, spent, ...) —
    the canonical statuses used by the dashboard, notifications, and health.
    """
    today = today or date.today()
    month_start = today.replace(day=1)
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    budget_rows = (
        await db.execute(select(Budget).where(Budget.user_id == user_id))
    ).scalars().all()
    days_in_month = (next_month_start - month_start).days
    days_elapsed = max((today - month_start).days + 1, 1)  # today counts as a day

    budgets = []
    for b in budget_rows:
        spent = await _spent_for_budget(db, user_id, b.category_id, month_start, next_month_start)
        amount = float(b.amount)

        # Unused budget from last month carries forward when rollover is on.
        carryover = 0.0
        if b.rollover:
            last_spent = await _spent_for_budget(db, user_id, b.category_id, last_month_start, month_start)
            carryover = round(max(amount - last_spent, 0), 2)

        effective_amount = amount + carryover
        available = round(effective_amount - spent, 2)
        # Project month-end spend from the current trend, but avoid extrapolating
        # a single fixed monthly bill (like rent or mortgage) into a fake repeat
        # charge across the whole month. Those should be measured against the
        # actual spend already posted for the month instead of a daily run rate.
        expense_count = await _expense_transaction_count(db, user_id, b.category_id, month_start, next_month_start)
        if spent > 0 and expense_count <= 1:
            projected = round(spent, 2)
        elif spent > 0:
            projected = round(spent / days_elapsed * days_in_month, 2)
        else:
            projected = 0.0
        # Classification is driven by actual spend against the effective limit
        # (unused budget rolls forward when rollover is on), not by a linear
        # projection. A budget that has spent up to its limit is "on track";
        # once spend reaches/exceeds the limit it is "at risk". The month-end
        # projection is still reported so the UI can show pace, but it does not
        # drive the status badge.
        if effective_amount > 0 and spent >= effective_amount:
            status = "at_risk"
        else:
            status = "on_track"
        budgets.append({
            "id": b.id,
            "name": b.name,
            "amount": amount,
            "rollover": bool(b.rollover),
            "carryover": carryover,
            "effective_amount": round(effective_amount, 2),
            "available": available,
            "spent": round(spent, 2),
            "progress_pct": round(spent / effective_amount * 100, 1) if effective_amount > 0 else 0.0,
            "projected": projected,
            "status": status,
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
        })
    return budgets