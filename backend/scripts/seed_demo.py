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


async def main() -> None:
    await init_db()
    async with async_session() as session:
        user = await _get_or_create_user(session)

        checking = await _get_or_create_account(session, user, "Checking", "checking", 20528.95)
        savings = await _get_or_create_account(session, user, "Savings", "savings", 2000.00)

        groceries = await _get_or_create_category(session, user, "Groceries", "expense")
        salary = await _get_or_create_category(session, user, "Salary", "income")

        # Transactions (skip if already seeded by date+description)
        seed_txs = [
            (TODAY - timedelta(days=1), -45.25, "Whole Foods", "WF", checking, groceries),
            (TODAY - timedelta(days=3), -9.99, "Netflix", None, checking, None),
            (TODAY - timedelta(days=5), -32.10, "Shell Gas Station", None, checking, None),
            (TODAY.replace(day=1), 8000.00, "Monthly salary", None, checking, salary),
        ]
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

        # Domain records
        if not (await session.execute(select(CreditCard).where(CreditCard.user_id == user.id))).scalar_one_or_none():
            session.add_all(
                [
                    CreditCard(user_id=user.id, name="Chase Sapphire Preferred", balance=2400.00, credit_limit=10000.00, apr=24.99, payment_due_date=TODAY + timedelta(days=10), min_payment=85.00),
                    CreditCard(user_id=user.id, name="Amex Blue Cash", balance=0.00, credit_limit=8000.00, apr=19.49, payment_due_date=None, min_payment=0.00),
                ]
            )
        if not (await session.execute(select(Debt).where(Debt.user_id == user.id))).scalar_one_or_none():
            session.add(
                Debt(user_id=user.id, name="Student Loan", type="student", principal=12000.00, interest_rate=5.5, min_payment=150.00, payment_due_date=TODAY + timedelta(days=5), remaining_term_months=96)
            )
        if not (await session.execute(select(Investment).where(Investment.user_id == user.id))).scalar_one_or_none():
            session.add_all(
                [
                    Investment(user_id=user.id, name="Vanguard Total Market", type="etf", symbol="VTI", cost_basis=10000.00, current_value=13250.00, account_name="Brokerage"),
                    Investment(user_id=user.id, name="Fidelity 401k", type="retirement", symbol=None, cost_basis=18000.00, current_value=22750.00, account_name="Fidelity"),
                ]
            )
        if not (await session.execute(select(SavingsGoal).where(SavingsGoal.user_id == user.id))).scalar_one_or_none():
            session.add(
                SavingsGoal(user_id=user.id, name="Emergency Fund", target_amount=15000.00, current_amount=6000.00, target_date=None)
            )
        if not (await session.execute(select(Bill).where(Bill.user_id == user.id))).scalar_one_or_none():
            session.add_all(
                [
                    Bill(user_id=user.id, name="Netflix", amount=15.99, due_date=TODAY + timedelta(days=2), frequency="monthly", auto_pay=True),
                    Bill(user_id=user.id, name="Rent", amount=1850.00, due_date=TODAY.replace(day=1), frequency="monthly", auto_pay=True),
                ]
            )
        if not (await session.execute(select(Budget).where(Budget.user_id == user.id))).scalar_one_or_none():
            session.add_all(
                [
                    Budget(user_id=user.id, name="Groceries", amount=600.00, period="monthly", category_id=groceries.id),
                    Budget(user_id=user.id, name="Fun", amount=300.00, period="monthly"),
                ]
            )

        await session.commit()
        print(f"Seeded user {user.email} (password: testpass123)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
