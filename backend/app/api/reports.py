"""Monthly reporting: income/expense breakdowns by category, account, and merchant."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Account, Category, Transaction
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, end


@router.get("/monthly")
async def monthly_report(
    year: int = date.today().year,
    month: int = date.today().month,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Structured monthly report for a given year/month.

    - income/expense/net plus the previous month for comparison
    - by_category: expense totals per category (incl. an Uncategorized row)
    - by_account: per-account income/expense/net
    - top_merchants: the 10 biggest expense merchants
    - daily_series: day-by-day income and expense for charting
    """
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="month must be between 1 and 12")
    user_id = current_user.id
    start, end = _month_bounds(year, month)

    # --- income & expense totals (this month + previous month) ---
    async def _sums(lo: date, hi: date) -> dict:
        income = (
            await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user_id,
                    Transaction.date >= lo,
                    Transaction.date < hi,
                    Transaction.amount > 0,
                )
            )
        ).scalar()
        expense = (
            await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user_id,
                    Transaction.date >= lo,
                    Transaction.date < hi,
                    Transaction.amount < 0,
                )
            )
        ).scalar()
        return {"income": round(float(income), 2), "expense": round(float(-expense), 2)}

    current = await _sums(start, end)
    prev_start, prev_end = _month_bounds(
        year - 1 if month == 1 else year, 12 if month == 1 else month - 1
    )
    previous = await _sums(prev_start, prev_end)

    # --- expense by category (single grouped query) ---
    by_category_rows = (
        await db.execute(
            select(
                Category.name,
                func.coalesce(func.sum(-Transaction.amount), 0),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= start,
                Transaction.date < end,
                Transaction.amount < 0,
            )
            .group_by(Category.name)
            .order_by(func.sum(-Transaction.amount).desc())
        )
    ).all()
    by_category = [
        {"name": name, "amount": round(float(amount), 2)} for name, amount in by_category_rows
    ]

    # Uncategorized expenses form their own line so the report always reconciles.
    uncategorized = (
        await db.execute(
            select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.date >= start,
                Transaction.date < end,
                Transaction.amount < 0,
                Transaction.category_id.is_(None),
            )
        )
    ).scalar()
    if float(uncategorized) > 0:
        by_category.append({"name": "Uncategorized", "amount": round(float(uncategorized), 2)})

    total_expense = current["expense"]
    for row in by_category:
        row["pct"] = round(row["amount"] / total_expense * 100, 1) if total_expense > 0 else 0.0

    # --- per-account income/expense/net (single grouped query) ---
    account_rows = (
        await db.execute(
            select(
                Account.id,
                Account.name,
                func.coalesce(
                    func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)), 0
                ),
            )
            .join(Transaction, Transaction.account_id == Account.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= start,
                Transaction.date < end,
            )
            .group_by(Account.id)
            .order_by(Account.name)
        )
    ).all()
    by_account = [
        {
            "id": acc_id,
            "name": name,
            "income": round(float(income), 2),
            "expense": round(float(expense), 2),
            "net": round(float(income) - float(expense), 2),
        }
        for acc_id, name, income, expense in account_rows
    ]

    # --- top merchants (grouped expense query) ---
    merchant_rows = (
        await db.execute(
            select(
                Transaction.merchant,
                func.sum(-Transaction.amount),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= start,
                Transaction.date < end,
                Transaction.amount < 0,
                Transaction.merchant.isnot(None),
            )
            .group_by(Transaction.merchant)
            .order_by(func.sum(-Transaction.amount).desc())
            .limit(10)
        )
    ).all()
    top_merchants = [
        {"merchant": merchant, "amount": round(float(amount), 2)}
        for merchant, amount in merchant_rows
    ]

    # --- daily series for charts (one query per direction, grouped by day) ---
    days_in_month = (end - start).days

    async def _daily(sign: str) -> list[float]:
        rows = (
            await db.execute(
                select(
                    func.extract("day", Transaction.date).label("day"),
                    func.sum(Transaction.amount),
                )
                .where(
                    Transaction.user_id == user_id,
                    Transaction.date >= start,
                    Transaction.date < end,
                    Transaction.amount > 0 if sign == "income" else Transaction.amount < 0,
                )
                .group_by("day")
            )
        ).all()
        by_day = {int(day): float(amount) for day, amount in rows}
        # Signed values: income is positive, expense is negative (matches the
        # transaction sign convention used everywhere else in the API).
        return [round(by_day.get(d, 0.0), 2) for d in range(1, days_in_month + 1)]

    daily_income = await _daily("income")
    daily_expense = await _daily("expense")

    return {
        "year": year,
        "month": month,
        "income": current["income"],
        "expense": current["expense"],
        "net": round(current["income"] - current["expense"], 2),
        "previous": previous,
        "by_category": by_category,
        "by_account": by_account,
        "top_merchants": top_merchants,
        "daily_series": [
            {"day": d, "income": daily_income[d - 1], "expense": daily_expense[d - 1]}
            for d in range(1, days_in_month + 1)
        ],
    }
