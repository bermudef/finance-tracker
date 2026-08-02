"""Recurring transaction processing.

Materializes due recurring transactions into the transactions table and
rolls their schedule forward. Reuses ``next_occurrence`` from the bills
service so day-of-month clamping (e.g. the 31st in a 30-day month) behaves
identically to bill scheduling.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import RecurringTransaction, Transaction
from app.services.bills import next_occurrence


async def process_due_recurring(
    db: AsyncSession,
    user_id: int,
    today: Optional[date] = None,
) -> list[Transaction]:
    """Create transactions for every recurring item whose next_date has passed.

    For each due item: post one Transaction on the item's next_date, then
    advance next_date to the following occurrence. Items stay active so the
    next due date keeps producing entries; pause via is_active=False.

    Returns the created transactions (empty list when nothing is due).
    """
    today = today or date.today()
    rows = (
        await db.execute(
            select(RecurringTransaction).where(
                RecurringTransaction.user_id == user_id,
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.next_date <= today,
            )
        )
    ).scalars().all()

    created = []
    for item in rows:
        posted_date = item.next_date
        created.append(
            Transaction(
                user_id=user_id,
                account_id=item.account_id,
                category_id=item.category_id,
                date=posted_date,
                amount=item.amount,
                description=f"Recurring: {item.name}",
                merchant=item.name,
                status="posted",
            )
        )
        # Roll forward from the occurrence we just posted, not from today, so
        # a missed week of processing cannot skip or duplicate dates.
        item.next_date = next_occurrence(
            posted_date, item.frequency, posted_date + timedelta(days=1)
        )

    if created:
        db.add_all(created)
        await db.commit()
        for tx in created:
            await db.refresh(tx)
    return created


async def list_recurring(
    db: AsyncSession,
    user_id: int,
) -> list[RecurringTransaction]:
    rows = (
        await db.execute(
            select(RecurringTransaction)
            .where(RecurringTransaction.user_id == user_id)
            .order_by(RecurringTransaction.next_date)
        )
    ).scalars().all()
    return rows
