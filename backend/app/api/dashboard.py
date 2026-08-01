from __future__ import annotations
from typing import Optional
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.domain import Bill, CreditCard, Debt, Investment, SavingsGoal
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
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
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
        # date.replace(month=x) breaks when x <= 0 (e.g. January minus 5 months),
        # so compute month/year arithmetically instead.
        offset = month_start.month - 1 - i
        year = month_start.year + offset // 12
        month_num = offset % 12 + 1
        first = date(year, month_num, 1)
        nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
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
    days_in_month = (next_month_start - month_start).days
    days_elapsed = max((today - month_start).days + 1, 1)  # today counts as a day
    budgets = []
    for b in budget_rows:
        spent_query = select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
            Transaction.date >= month_start,
            Transaction.date < next_month_start,
            Transaction.amount < 0,
            Transaction.user_id == user_id,
        )
        if b.category_id is None:
            # A budget without a category is a general budget: it tracks
            # every expense for the period, not just uncategorized ones.
            pass
        else:
            spent_query = spent_query.where(Transaction.category_id == b.category_id)
        spent = (await db.execute(spent_query)).scalar()
        amount = float(b.amount)
        # Project month-end spend from what's already been spent: if you've
        # spent $60 of a $100 budget in the first 10 days, you're on pace to
        # spend ~$180. That forward-looking signal drives the status badge.
        # On the last day of the month the projection is final, so a budget
        # that's merely >75% used is on track, not at risk.
        projected = (
            round(float(spent) / days_elapsed * days_in_month, 2)
            if float(spent) > 0
            else 0.0
        )
        if amount > 0 and projected >= amount:
            status = "over"
        elif amount > 0 and days_elapsed < days_in_month and projected >= 0.75 * amount:
            status = "at_risk"
        else:
            status = "on_track"
        budgets.append({
            "id": b.id,
            "name": b.name,
            "amount": amount,
            "spent": round(float(spent), 2),
            "progress_pct": round(float(spent) / amount * 100, 1) if amount > 0 else 0.0,
            "projected": projected,
            "status": status,
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
        })

    # --- Wealth: investments, debt, net worth, savings goals ---
    investment_rows = (
        await db.execute(select(Investment).where(Investment.user_id == user_id))
    ).scalars().all()
    investments_value = sum(float(i.current_value or 0) for i in investment_rows)
    investments_cost = sum(float(i.cost_basis or 0) for i in investment_rows)
    investments_gain = investments_value - investments_cost

    credit_card_rows = (
        await db.execute(select(CreditCard).where(CreditCard.user_id == user_id))
    ).scalars().all()
    credit_card_balance = sum(float(c.balance or 0) for c in credit_card_rows)

    debt_rows = (
        await db.execute(select(Debt).where(Debt.user_id == user_id))
    ).scalars().all()
    debt_total = credit_card_balance + sum(float(d.principal or 0) for d in debt_rows)
    debt_by_type: dict[str, float] = {}
    for d in debt_rows:
        debt_by_type[d.type] = round(
            debt_by_type.get(d.type, 0.0) + float(d.principal or 0), 2
        )
    if credit_card_balance:
        debt_by_type["credit_card"] = round(
            debt_by_type.get("credit_card", 0.0) + credit_card_balance, 2
        )

    net_worth = total_balance + investments_value - debt_total

    goal_rows = (
        await db.execute(
            select(SavingsGoal).where(
                SavingsGoal.user_id == user_id, SavingsGoal.is_active.is_(True)
            )
        )
    ).scalars().all()
    savings_goals = []
    for g in goal_rows:
        target = float(g.target_amount or 0)
        current = float(g.current_amount or 0)
        savings_goals.append({
            "id": g.id,
            "name": g.name,
            "target_amount": target,
            "current_amount": current,
            "progress_pct": round(current / target * 100, 1) if target > 0 else 0.0,
            "target_date": g.target_date.isoformat() if g.target_date else None,
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
        "net_worth": round(net_worth, 2),
        "investments": {
            "total_value": round(investments_value, 2),
            "total_cost_basis": round(investments_cost, 2),
            "gain_loss": round(investments_gain, 2),
        },
        "debt": {
            "total": round(debt_total, 2),
            "by_type": dict(sorted(debt_by_type.items(), key=lambda kv: -kv[1])),
        },
        "savings_goals": savings_goals,
    }
