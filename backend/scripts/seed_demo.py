"""Seed the database with a demo user and realistic sample data.

Idempotent: safe to run repeatedly. Usage:

    DATABASE_URL=postgresql+asyncpg://finance:...@localhost:5432/finance_db \
        ./venv/bin/python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import engine, async_session, init_db
from app.models.finance import Account, Budget, Category, Transaction
from app.models.user import User

import app.models.finance  # noqa: F401  register tables
import app.models.user  # noqa: F401
import app.models.password_reset  # noqa: F401
import app.models.domain  # noqa: F401
from app.models.domain import Bill, CreditCard, Debt, Investment, SavingsGoal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TODAY = date.today()


async def _get_or_create_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email="test@example.com",
            hashed_password=pwd_context.hash("testpass123"),
            full_name="Test User",
            is_active=True,
        )
        session.add(user)
        await session.flush()
    return user


async def _get_or_create_account(session: AsyncSession, user: User, name: str, type_: str, opening: float) -> Account:
    result = await session.execute(
        select(Account).where(Account.user_id == user.id, Account.name == name)
    )
    account = result.scalar_one_or_none()
    if account is None:
        account = Account(user_id=user.id, name=name, type=type_, opening_balance=opening)
        session.add(account)
        await session.flush()
    return account


async def _get_or_create_category(session: AsyncSession, user: User, name: str, type_: str) -> Category:
    result = await session.execute(
        select(Category).where(Category.user_id == user.id, Category.name == name)
    )
    category = result.scalar_one_or_none()
    if category is None:
        category = Category(user_id=user.id, name=name, type=type_)
        session.add(category)
        await session.flush()
    return category


async def _get_or_create_by_name(session: AsyncSession, user: User, model, name: str, **kw):
    """Get a row by (user, name) on any user-scoped model, creating it or
    converging existing rows to `kw`. Keeps the seed idempotent across reruns
    even when the previous run created multiple rows."""
    result = await session.execute(
        select(model).where(model.user_id == user.id, model.name == name)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        obj = model(user_id=user.id, name=name, **kw)
        session.add(obj)
        await session.flush()
        return obj
    changed = False
    for key, value in kw.items():
        if getattr(obj, key) != value:
            setattr(obj, key, value)
            changed = True
    if changed:
        session.add(obj)  # mark dirty for the commit
    return obj


async def main() -> None:
    await init_db()
    async with async_session() as session:
        user = await _get_or_create_user(session)

        checking = await _get_or_create_account(session, user, "Checking", "checking", 20528.95)
        savings = await _get_or_create_account(session, user, "Savings", "savings", 2000.00)

        groceries = await _get_or_create_category(session, user, "Groceries", "expense")
        salary = await _get_or_create_category(session, user, "Salary", "income")
        rent = await _get_or_create_category(session, user, "Rent", "expense")
        utilities = await _get_or_create_category(session, user, "Utilities", "expense")
        dining = await _get_or_create_category(session, user, "Dining", "expense")
        gas = await _get_or_create_category(session, user, "Gas", "expense")
        insurance = await _get_or_create_category(session, user, "Insurance", "expense")

        # Recurring transactions across the last 3 months so the dashboard
        # series, statements, and health score have realistic depth. Each
        # pattern is a function of the month's first day.
        last_months = []
        for i in range(2, -1, -1):
            offset = TODAY.month - 1 - i
            year = TODAY.year + offset // 12
            last_months.append(date(year, offset % 12 + 1, 1))

        monthly_patterns = [
            lambda m: (m.replace(day=1), 8000.00, "Monthly salary", None, checking, salary),
            lambda m: (m.replace(day=3), -1850.00, "Rent", None, checking, rent),
            lambda m: (m.replace(day=5), -560.00, "Groceries", "Whole Foods", checking, groceries),
            lambda m: (m.replace(day=12), -135.00, "Electric & water", None, checking, utilities),
            lambda m: (m.replace(day=15), -95.00, "Dining out", "Local Bistro", checking, dining),
            lambda m: (m.replace(day=20), -52.00, "Gas", "Shell", checking, gas),
            lambda m: (m.replace(day=22), -240.00, "Health insurance", None, checking, insurance),
            lambda m: (m.replace(day=25), -15.99, "Netflix", "Netflix", checking, None),
        ]

        # One-off recent transactions (idempotent by description + date).
        seed_txs = [
            (TODAY - timedelta(days=1), -45.25, "Whole Foods", "WF", checking, groceries),
            (TODAY - timedelta(days=3), -32.10, "Shell Gas Station", None, checking, gas),
            (TODAY - timedelta(days=6), -85.00, "Dinner with friends", "Pasta Palace", checking, dining),
        ]

        for month_start in last_months:
            seed_txs += [pattern(month_start) for pattern in monthly_patterns]

        for tx_date, amount, desc, merchant, account, category in seed_txs:
            exists = await session.execute(
                select(Transaction.id).where(
                    Transaction.user_id == user.id,
                    Transaction.description == desc,
                    Transaction.date == tx_date,
                )
            )
            if exists.scalar_one_or_none() is None:
                session.add(
                    Transaction(
                        user_id=user.id,
                        account_id=account.id,
                        category_id=category.id if category else None,
                        date=tx_date,
                        amount=amount,
                        description=desc,
                        merchant=merchant,
                    )
                )

        # Domain records — all per-name idempotent (safe across reruns even when
        # the previous run created multiple rows).
        await _get_or_create_by_name(
            session, user, CreditCard, "Chase Sapphire Preferred",
            balance=2400.00, credit_limit=10000.00, apr=24.99,
            payment_due_date=TODAY + timedelta(days=10), min_payment=85.00,
        )
        await _get_or_create_by_name(
            session, user, CreditCard, "Amex Blue Cash",
            balance=0.00, credit_limit=8000.00, apr=19.49,
            payment_due_date=None, min_payment=0.00,
        )
        # Debts — sized so the payoff optimizer demo diverges: avalanche targets
        # the high-APR Chase card first, while snowball targets the smaller
        # Student Loan first.
        await _get_or_create_by_name(
            session, user, Debt, "Student Loan",
            type="student", principal=6000.00, interest_rate=5.5,
            min_payment=150.00, payment_due_date=TODAY + timedelta(days=5),
            remaining_term_months=48,
        )
        await _get_or_create_by_name(
            session, user, Debt, "Chase Sapphire",
            type="credit_card", principal=12000.00, interest_rate=24.99,
            min_payment=250.00, payment_due_date=TODAY + timedelta(days=15),
            remaining_term_months=None,
        )
        await _get_or_create_by_name(
            session, user, Investment, "Vanguard Total Market",
            type="etf", symbol="VTI", cost_basis=10000.00,
            current_value=13250.00, account_name="Brokerage",
        )
        await _get_or_create_by_name(
            session, user, Investment, "Fidelity 401k",
            type="retirement", symbol=None, cost_basis=18000.00,
            current_value=22750.00, account_name="Fidelity",
        )
        await _get_or_create_by_name(
            session, user, SavingsGoal, "Emergency Fund",
            target_amount=15000.00, current_amount=6000.00, target_date=None,
        )
        await _get_or_create_by_name(
            session, user, Bill, "Netflix",
            amount=15.99, due_date=TODAY + timedelta(days=2),
            frequency="monthly", auto_pay=True,
        )
        await _get_or_create_by_name(
            session, user, Bill, "Rent",
            amount=1850.00, due_date=TODAY.replace(day=1),
            frequency="monthly", auto_pay=True,
        )
        await _get_or_create_by_name(
            session, user, Budget, "Groceries",
            amount=700.00, period="monthly", category_id=groceries.id,
        )
        await _get_or_create_by_name(
            session, user, Budget, "Fun",
            amount=250.00, period="monthly", category_id=dining.id,
        )
        await _get_or_create_by_name(
            session, user, Budget, "Everyday spending",
            amount=3300.00, period="monthly", category_id=None,
        )

        await session.commit()
        print(f"Seeded user {user.email} (password: testpass123)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
