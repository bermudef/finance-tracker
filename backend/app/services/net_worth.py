"""Net worth history series.

Net worth is tracked as a point-in-time figure: liquid account balances
(opening balance plus the sum of transactions up to month end) plus the
current value of investments, minus active debt principal and credit card
balances.

Only cash-flow history is stored, so investments and debt are held constant
at their current values across the window. The returned series includes
``constant_components`` so the UI can be explicit about that assumption.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import CreditCard, Debt, Investment
from app.models.finance import Account, Transaction

DEFAULT_MONTHS = 12
MAX_MONTHS = 24


def _month_bounds(start: date, count: int) -> list[tuple[date, date]]:
    """Return (first_day, day_after_last) for the last `count` months ending with `start`."""
    bounds = []
    month_start = start.replace(day=1)
    for i in range(count - 1, -1, -1):
        offset = month_start.month - 1 - i
        year = month_start.year + offset // 12
        month = offset % 12 + 1
        first = date(year, month, 1)
        nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        bounds.append((first, nxt))
    return bounds


async def compute_net_worth_series(
    db: AsyncSession,
    user_id: int,
    months: int = DEFAULT_MONTHS,
) -> dict[str, Any]:
    """Monthly net worth for the last `months` months (newest last)."""
    months = max(3, min(months, MAX_MONTHS))
    today = date.today()
    bounds = _month_bounds(today, months)

    accounts = (
        await db.execute(select(Account).where(Account.user_id == user_id))
    ).scalars().all()
    txns = (
        await db.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.date <= today,
                Transaction.status != "pending",
            )
            .order_by(Transaction.date)
        )
    ).scalars().all()

    # Running balance per account as of each month end. Transactions are
    # already sorted by date, so one pass over the list produces every
    # month's balance without N+1 queries.
    balances = {a.id: float(a.opening_balance or 0) for a in accounts}
    month_total = []  # (end_date, total_balance)
    tx_index = 0
    for first, nxt in bounds:
        while tx_index < len(txns) and txns[tx_index].date < nxt:
            t = txns[tx_index]
            balances[t.account_id] = balances.get(t.account_id, 0.0) + float(t.amount)
            tx_index += 1
        month_total.append((nxt - timedelta(days=1), round(sum(balances.values()), 2)))

    investments_value = sum(
        float(i.current_value or 0)
        for i in (await db.execute(select(Investment).where(Investment.user_id == user_id))).scalars()
    )
    debt_total = sum(
        float(d.principal or 0)
        for d in (
            await db.execute(
                select(Debt).where(Debt.user_id == user_id, Debt.is_active.is_(True))
            )
        ).scalars()
    )
    credit_card_balance = sum(
        float(c.balance or 0)
        for c in (
            await db.execute(
                select(CreditCard).where(
                    CreditCard.user_id == user_id, CreditCard.is_active.is_(True)
                )
            )
        ).scalars()
    )
    debt_total += credit_card_balance

    series = []
    for end_date, total_balance in month_total:
        net_worth = total_balance + investments_value - debt_total
        series.append(
            {
                "month": end_date.strftime("%b %Y"),
                "net_worth": round(net_worth, 2),
            }
        )

    return {
        "months": months,
        "series": series,
        "investments_value": round(investments_value, 2),
        "debt_total": round(debt_total, 2),
        "note": "Investments and debt are held constant at current values; only cash-flow history varies.",
    }
