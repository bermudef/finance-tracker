from __future__ import annotations
from typing import Optional
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Account, Budget, Category, Transaction
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id
    today = date.today()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    balance_rows = (
        await db.execute(select(Account).where(Account.user_id == user_id))
    ).scalars().all()
    accounts = []
    total_balance = 0.0
    for a in balance_rows:
        opening = float(a.opening_balance or 0)
        tx_sum = (
            await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.account_id == a.id
                )
            )
        ).scalar()
        balance = opening + float(tx_sum)
        total_balance += balance
        accounts.append({
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "currency": a.currency,
            "balance": round(balance, 2),
        })

    income_this_month = (
        await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.date >= month_start,
                Transaction.amount > 0,
                Transaction.user_id == user_id,
            )
        )
    ).scalar()
    expense_this_month = (
        await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.date >= month_start,
                Transaction.amount < 0,
                Transaction.user_id == user_id,
            )
        )
    ).scalar()

    income_last_month = (
        await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.date >= last_month_start,
                Transaction.date < month_start,
                Transaction.amount > 0,
                Transaction.user_id == user_id,
            )
        )
    ).scalar()
    expense_last_month = (
        await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.date >= last_month_start,
                Transaction.date < month_start,
                Transaction.amount < 0,
                Transaction.user_id == user_id,
            )
        )
    ).scalar()

    cat_stmt = (
        select(Category, func.coalesce(func.sum(-Transaction.amount), 0))
        .outerjoin(Transaction, Transaction.category_id == Category.id)
        .where(
            Category.type == "expense",
            Category.user_id == user_id,
            Transaction.date >= month_start,
            Transaction.amount < 0,
        )
    )
    cat_rows = await db.execute(
        cat_stmt.group_by(Category.id)
        .order_by(func.sum(-Transaction.amount).desc())
    )
    spending_by_category = [
        {"name": c.name, "amount": round(float(amount), 2), "color": c.color}
        for c, amount in cat_rows.all()
        if amount > 0
    ]

    last_6_months = []
    for i in range(5, -1, -1):
        first = month_start.replace(month=month_start.month - i, day=1)
        nxt = (first + timedelta(days=32)).replace(day=1)
        inc = (
            await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.date >= first,
                    Transaction.date < nxt,
                    Transaction.amount > 0,
                    Transaction.user_id == user_id,
                )
            )
        ).scalar()
        exp = (
            await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.date >= first,
                    Transaction.date < nxt,
                    Transaction.amount < 0,
                    Transaction.user_id == user_id,
                )
            )
        ).scalar()
        last_6_months.append({
            "month": first.strftime("%b %Y"),
            "income": round(float(inc), 2),
            "expense": round(float(-exp), 2),
        })

    budget_rows = (
        await db.execute(select(Budget).where(Budget.user_id == user_id))
    ).scalars().all()
    budgets = []
    for b in budget_rows:
        spent = (
            await db.execute(
                select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
                    Transaction.date >= month_start,
                    Transaction.category_id == b.category_id,
                    Transaction.amount < 0,
                    Transaction.user_id == user_id,
                )
            )
        ).scalar()
        budgets.append({
            "id": b.id,
            "name": b.name,
            "amount": float(b.amount),
            "spent": round(float(spent), 2),
        })

    return {
        "total_balance": round(total_balance, 2),
        "accounts": accounts,
        "monthly": {
            "income": round(float(income_this_month), 2),
            "expense": round(float(-expense_this_month), 2),
            "net": round(float(income_this_month) + float(expense_this_month), 2),
            "last_month_income": round(float(income_last_month), 2),
            "last_month_expense": round(float(-expense_last_month), 2),
        },
        "spending_by_category": spending_by_category,
        "monthly_series": last_6_months,
        "budgets": budgets,
    }
