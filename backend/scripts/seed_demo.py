"""Seed the database with realistic demo households and transaction history.

The seed data begins at 2026-01-01 and continues through today so the app
shows financial history consistent with each household profile.
"""
from __future__ import annotations

import os
import sys

# Ensure the backend directory (containing the app/ package) is importable
# regardless of the caller's CWD.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import math
from datetime import date, timedelta
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import engine, async_session, init_db
from app.models.finance import Account, Budget, Category, RecurringTransaction, Transaction
from app.models.user import User

import app.models.finance  # noqa: F401  register tables
import app.models.user  # noqa: F401
import app.models.password_reset  # noqa: F401
import app.models.domain  # noqa: F401
from app.models.domain import Bill, CreditCard, Debt, Household, HouseholdMembership, Investment, SavingsGoal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

START_DATE = date(2026, 1, 1)
TODAY = date.today()


def _dynamic_amount(base_amount: float, month_index: int, family_offset: int, variability: float) -> float:
    """Return a stronger month-over-month variation that feels like real life.

    The variations are deterministic and household-specific so nearby months can
    no longer collapse into the same totals.
    """
    amplitude = max(variability, 0.25)
    seasonal = 1 + amplitude * math.sin((month_index + family_offset + 1) * 1.3)
    cadence = 1 + amplitude * 0.9 * math.cos((month_index + 1) * 1.9 + family_offset)
    pulse = 1 + amplitude * 1.1 * (((month_index + family_offset) % 6) - 2.5) / 2.5
    adjusted = abs(base_amount) * seasonal * cadence * pulse
    return round(adjusted, 2)


SCENARIOS: list[dict[str, Any]] = [
    {
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User",
        "household_name": "Test Household",
        "expense_variation": 0.08,
        "family_offset": 1,
        "accounts": [
            ("Checking", "checking", 15250.00),
            ("Savings", "savings", 6800.00),
        ],
        "categories": [
            ("Salary", "income"),
            ("Rent", "expense"),
            ("Groceries", "expense"),
            ("Utilities", "expense"),
            ("Dining", "expense"),
            ("Fun", "expense"),
            ("Gas", "expense"),
            ("Insurance", "expense"),
            ("Entertainment", "expense"),
            ("Subscriptions", "expense"),
            ("Savings Transfer", "expense"),
        ],
        "budgets": [
            ("Housing", 0.34, "Rent"),
            ("Groceries", 0.12, "Groceries"),
            ("Fun", 0.07, "Fun"),
        ],
        "monthly_transactions": [
            {"day": 1, "amount": 8700.00, "description": "Monthly salary", "merchant": None, "account": "Checking", "category": "Salary"},
            {"day": 6, "amount": -650.00, "description": "Whole Foods", "merchant": "Whole Foods", "account": "Checking", "category": "Groceries"},
            {"day": 15, "amount": -220.00, "description": "Dinner out", "merchant": "Local Bistro", "account": "Checking", "category": "Fun"},
            {"day": 18, "amount": -175.00, "description": "Gas fill-up", "merchant": "Shell", "account": "Checking", "category": "Gas"},
            {"day": 26, "amount": -500.00, "description": "Savings transfer", "merchant": None, "account": "Checking", "category": "Savings Transfer"},
            {"day": 28, "amount": -240.00, "description": "Movie night", "merchant": "AMC", "account": "Checking", "category": "Fun"},
        ],
        "recurring_transactions": [
            {"name": "Apartment rent", "amount": -2150.00, "day": 3, "account": "Checking", "category": "Rent", "frequency": "monthly"},
            {"name": "Streaming bundle", "amount": -140.00, "day": 24, "account": "Checking", "category": "Subscriptions", "frequency": "monthly"},
            {"name": "Electric & water", "amount": -320.00, "day": 12, "account": "Checking", "category": "Utilities", "frequency": "monthly"},
            {"name": "Health insurance", "amount": -410.00, "day": 22, "account": "Checking", "category": "Insurance", "frequency": "monthly"},
        ],
        "credit_cards": [
            ("Chase Sapphire Preferred", 2600.00, 9000.00, 18.99, 12),
        ],
        "debts": [
            ("Student Loan", "student", 9800.00, 5.1, 210.00, 36),
        ],
        "investments": [
            ("Fidelity 401k", "retirement", None, 24500.00, 32800.00, "Fidelity"),
            ("Vanguard Brokerage", "etf", "VTI", 8500.00, 11350.00, "Brokerage"),
        ],
        "savings_goals": [
            ("Home Down Payment", 30000.00, 14500.00, None),
        ],
        "bills": [
            ("Internet", 79.99, 3, "monthly", True),
            ("Spotify", 11.99, 8, "monthly", True),
        ],
    },
    {
        "email": "parker.family@example.com",
        "password": "ParkerFamily!2025",
        "full_name": "Parker Family",
        "household_name": "Parker Family",
        "expense_variation": 0.09,
        "family_offset": 3,
        "accounts": [
            ("Checking", "checking", 38500.00),
            ("Savings", "savings", 61000.00),
            ("Brokerage", "cash", 19500.00),
        ],
        "categories": [
            ("Salary", "income"),
            ("Side Hustle", "income"),
            ("Mortgage", "expense"),
            ("Groceries", "expense"),
            ("Utilities", "expense"),
            ("Gas", "expense"),
            ("Dining", "expense"),
            ("Fun", "expense"),
            ("Insurance", "expense"),
            ("Travel", "expense"),
            ("Subscriptions", "expense"),
            ("Savings Transfer", "expense"),
        ],
        "budgets": [
            ("Housing", 0.34, "Mortgage"),
            ("Food", 0.12, "Groceries"),
            ("Fun", 0.05, "Fun"),
        ],
        "monthly_transactions": [
            {"day": 1, "amount": 11600.00, "description": "Primary salary", "merchant": None, "account": "Checking", "category": "Salary"},
            {"day": 2, "amount": 1200.00, "description": "Side gig income", "merchant": None, "account": "Checking", "category": "Side Hustle"},
            {"day": 5, "amount": -760.00, "description": "Groceries", "merchant": "Whole Foods", "account": "Checking", "category": "Groceries"},
            {"day": 14, "amount": -190.00, "description": "Fuel", "merchant": "Shell", "account": "Checking", "category": "Gas"},
            {"day": 17, "amount": -310.00, "description": "Dinner date", "merchant": "Pasta Palace", "account": "Checking", "category": "Fun"},
            {"day": 27, "amount": -950.00, "description": "Vacation savings", "merchant": None, "account": "Checking", "category": "Savings Transfer"},
            {"day": 29, "amount": -430.00, "description": "Weekend trip", "merchant": "Airbnb", "account": "Checking", "category": "Travel"},
        ],
        "recurring_transactions": [
            {"name": "Mortgage payment", "amount": -2750.00, "day": 3, "account": "Checking", "category": "Mortgage", "frequency": "monthly"},
            {"name": "Electric & water", "amount": -420.00, "day": 10, "account": "Checking", "category": "Utilities", "frequency": "monthly"},
            {"name": "Home insurance", "amount": -520.00, "day": 20, "account": "Checking", "category": "Insurance", "frequency": "monthly"},
            {"name": "Streaming bundle", "amount": -140.00, "day": 24, "account": "Checking", "category": "Subscriptions", "frequency": "monthly"},
        ],
        "credit_cards": [
            ("Chase Freedom Unlimited", 4100.00, 16000.00, 19.80, 17),
        ],
        "debts": [
            ("Auto Loan", "auto", 14500.00, 4.70, 410.00, 48),
        ],
        "investments": [
            ("Parker 401k", "retirement", None, 72000.00, 96050.00, "Fidelity"),
            ("Vanguard Index Fund", "etf", "VOO", 18000.00, 24500.00, "Brokerage"),
        ],
        "savings_goals": [
            ("Emergency Fund", 50000.00, 36000.00, None),
        ],
        "bills": [
            ("Internet", 89.99, 2, "monthly", True),
            ("Cell Phone", 98.00, 12, "monthly", True),
        ],
    },
    {
        "email": "nguyen.family@example.com",
        "password": "NguyenFamily!2025",
        "full_name": "Nguyen Family",
        "household_name": "Nguyen Family",
        "expense_variation": 0.14,
        "family_offset": 5,
        "accounts": [
            ("Checking", "checking", 12000.00),
            ("Savings", "savings", 8900.00),
            ("Emergency Fund", "savings", 4200.00),
        ],
        "categories": [
            ("Salary", "income"),
            ("Side Income", "income"),
            ("Rent", "expense"),
            ("Groceries", "expense"),
            ("Childcare", "expense"),
            ("Utilities", "expense"),
            ("Gas", "expense"),
            ("Dining", "expense"),
            ("Fun", "expense"),
            ("Insurance", "expense"),
            ("Medical", "expense"),
            ("Transportation", "expense"),
            ("Debt Payment", "expense"),
            ("Subscriptions", "expense"),
            ("Savings Transfer", "expense"),
        ],
        "budgets": [
            ("Housing", 0.38, "Rent"),
            ("Groceries", 0.15, "Groceries"),
            ("Childcare", 0.22, "Childcare"),
            ("Fun", 0.05, "Fun"),
        ],
        "monthly_transactions": [
            {"day": 1, "amount": 8200.00, "description": "Paycheck", "merchant": None, "account": "Checking", "category": "Salary"},
            {"day": 2, "amount": 480.00, "description": "Freelance project", "merchant": None, "account": "Checking", "category": "Side Income"},
            {"day": 5, "amount": -780.00, "description": "Groceries", "merchant": "Trader Joe's", "account": "Checking", "category": "Groceries"},
            {"day": 15, "amount": -220.00, "description": "Fuel", "merchant": "Chevron", "account": "Checking", "category": "Gas"},
            {"day": 17, "amount": -280.00, "description": "Family dinner", "merchant": "Panda Express", "account": "Checking", "category": "Fun"},
            {"day": 22, "amount": -180.00, "description": "School supplies", "merchant": "Target", "account": "Checking", "category": "Medical"},
            {"day": 24, "amount": -420.00, "description": "Debt payment", "merchant": None, "account": "Checking", "category": "Debt Payment"},
            {"day": 26, "amount": -350.00, "description": "Savings transfer", "merchant": None, "account": "Checking", "category": "Savings Transfer"},
        ],
        "recurring_transactions": [
            {"name": "Apartment rent", "amount": -2450.00, "day": 3, "account": "Checking", "category": "Rent", "frequency": "monthly"},
            {"name": "Childcare", "amount": -1550.00, "day": 7, "account": "Checking", "category": "Childcare", "frequency": "monthly"},
            {"name": "Utilities", "amount": -340.00, "day": 12, "account": "Checking", "category": "Utilities", "frequency": "monthly"},
            {"name": "Car insurance", "amount": -310.00, "day": 18, "account": "Checking", "category": "Insurance", "frequency": "monthly"},
            {"name": "Streaming bundle", "amount": -140.00, "day": 24, "account": "Checking", "category": "Subscriptions", "frequency": "monthly"},
        ],
        "credit_cards": [
            ("Capital One Savor", 6200.00, 11000.00, 21.90, 15),
        ],
        "debts": [
            ("Auto Loan", "auto", 12300.00, 4.90, 350.00, 42),
            ("Student Loan", "student", 19100.00, 5.20, 330.00, 54),
        ],
        "investments": [
            ("Roth IRA", "retirement", None, 21500.00, 30400.00, "Fidelity"),
            ("Brokerage Account", "etf", "QQQ", 9500.00, 12950.00, "Robinhood"),
        ],
        "savings_goals": [
            ("Emergency Fund", 20000.00, 8200.00, None),
        ],
        "bills": [
            ("Internet", 72.99, 3, "monthly", True),
            ("Cell Phone", 95.00, 5, "monthly", True),
        ],
    },
    {
        "email": "garcia.family@example.com",
        "password": "GarciaFamily!2025",
        "full_name": "Garcia Family",
        "household_name": "Garcia Family",
        "expense_variation": 0.22,
        "family_offset": 7,
        "accounts": [
            ("Checking", "checking", 2400.00),
            ("Savings", "savings", 950.00),
            ("Cash", "cash", 420.00),
        ],
        "categories": [
            ("Salary", "income"),
            ("Rent", "expense"),
            ("Groceries", "expense"),
            ("Childcare", "expense"),
            ("Utilities", "expense"),
            ("Gas", "expense"),
            ("Dining", "expense"),
            ("Fun", "expense"),
            ("Insurance", "expense"),
            ("Medical", "expense"),
            ("Debt Payment", "expense"),
            ("Subscriptions", "expense"),
            ("Transportation", "expense"),
        ],
        "budgets": [
            ("Housing", 0.42, "Rent"),
            ("Food", 0.17, "Groceries"),
            ("Essentials", 0.10, "Utilities"),
            ("Fun", 0.06, "Fun"),
        ],
        "monthly_transactions": [
            {"day": 1, "amount": 6100.00, "description": "Main paycheck", "merchant": None, "account": "Checking", "category": "Salary"},
            {"day": 6, "amount": -850.00, "description": "Groceries", "merchant": "Aldi", "account": "Checking", "category": "Groceries"},
            {"day": 15, "amount": -270.00, "description": "Fuel", "merchant": "Exxon", "account": "Checking", "category": "Gas"},
            {"day": 18, "amount": -250.00, "description": "Fast food", "merchant": "McDonald's", "account": "Checking", "category": "Fun"},
            {"day": 22, "amount": -200.00, "description": "Doctor visit", "merchant": None, "account": "Checking", "category": "Medical"},
            {"day": 25, "amount": -520.00, "description": "Debt payment", "merchant": None, "account": "Checking", "category": "Debt Payment"},
        ],
        "recurring_transactions": [
            {"name": "Rent payment", "amount": -2250.00, "day": 3, "account": "Checking", "category": "Rent", "frequency": "monthly"},
            {"name": "Childcare", "amount": -1000.00, "day": 8, "account": "Checking", "category": "Childcare", "frequency": "monthly"},
            {"name": "Utilities", "amount": -390.00, "day": 11, "account": "Checking", "category": "Utilities", "frequency": "monthly"},
            {"name": "Car insurance", "amount": -310.00, "day": 20, "account": "Checking", "category": "Insurance", "frequency": "monthly"},
            {"name": "Streaming bundle", "amount": -140.00, "day": 24, "account": "Checking", "category": "Subscriptions", "frequency": "monthly"},
            {"name": "Phone + streaming", "amount": -120.00, "day": 27, "account": "Checking", "category": "Subscriptions", "frequency": "monthly"},
        ],
        "credit_cards": [
            ("Citi Simplicity", 14900.00, 18000.00, 26.24, 21),
        ],
        "debts": [
            ("Personal Loan", "personal", 8600.00, 12.50, 290.00, 32),
            ("Car Loan", "auto", 11800.00, 7.30, 360.00, 48),
        ],
        "investments": [
            ("Brokerage Small Balance", "etf", "SCHD", 2100.00, 2450.00, "Brokerage"),
        ],
        "savings_goals": [
            ("Debt Freedom", 15000.00, 2400.00, None),
        ],
        "bills": [
            ("Internet", 68.99, 4, "monthly", True),
            ("Cell Phone", 88.00, 10, "monthly", True),
        ],
    },
]


async def _get_or_create_user(session: AsyncSession, email: str, password: str, full_name: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            hashed_password=pwd_context.hash(password),
            full_name=full_name,
            is_active=True,
        )
        session.add(user)
        await session.flush()
    else:
        user.full_name = full_name
        user.is_active = True
    return user


async def _get_or_create_household(session: AsyncSession, user: User, household_name: str) -> Household:
    result = await session.execute(
        select(Household).where(Household.created_by == user.id, Household.name == household_name)
    )
    household = result.scalar_one_or_none()
    if household is None:
        household = Household(name=household_name, created_by=user.id)
        session.add(household)
        await session.flush()

    membership = await session.execute(
        select(HouseholdMembership).where(
            HouseholdMembership.household_id == household.id,
            HouseholdMembership.user_id == user.id,
        )
    )
    membership_obj = membership.scalar_one_or_none()
    if membership_obj is None:
        session.add(HouseholdMembership(household_id=household.id, user_id=user.id, role="owner"))
    return household


async def _get_or_create_account(session: AsyncSession, user: User, name: str, type_: str, opening: float) -> Account:
    result = await session.execute(
        select(Account).where(Account.user_id == user.id, Account.name == name)
    )
    account = result.scalar_one_or_none()
    if account is None:
        account = Account(user_id=user.id, name=name, type=type_, opening_balance=opening)
        session.add(account)
        await session.flush()
    else:
        account.type = type_
        account.opening_balance = opening
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
    else:
        category.type = type_
    return category


async def _get_or_create_by_name(session: AsyncSession, user: User, model, name: str, **kw):
    result = await session.execute(select(model).where(model.user_id == user.id, model.name == name))
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
        session.add(obj)
    return obj


async def _ensure_transaction(
    session: AsyncSession,
    user: User,
    account: Account,
    category: Category | None,
    tx_date: date,
    amount: float,
    description: str,
    merchant: str | None,
) -> None:
    exists = await session.execute(
        select(Transaction.id).where(
            Transaction.user_id == user.id,
            Transaction.account_id == account.id,
            Transaction.description == description,
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
                description=description,
                merchant=merchant,
            )
        )


async def _ensure_recurring_transaction(
    session: AsyncSession,
    user: User,
    account: Account,
    category: Category | None,
    item: dict[str, Any],
) -> None:
    query = select(RecurringTransaction.id).where(
        RecurringTransaction.user_id == user.id,
        RecurringTransaction.name == item["name"],
        RecurringTransaction.account_id == account.id,
    )
    if category is not None:
        query = query.where(RecurringTransaction.category_id == category.id)
    else:
        query = query.where(RecurringTransaction.category_id.is_(None))

    exists = await session.execute(query)
    if exists.scalar_one_or_none() is not None:
        return

    first_due = date(2026, 1, min(int(item["day"]), 28))
    session.add(
        RecurringTransaction(
            user_id=user.id,
            account_id=account.id,
            category_id=category.id if category else None,
            name=item["name"],
            amount=float(item["amount"]),
            frequency=item.get("frequency", "monthly"),
            next_date=first_due,
            notes=item.get("notes"),
        )
    )


async def _reset_profile_data(session: AsyncSession, user: User) -> None:
    for model in (Transaction, RecurringTransaction, Budget, Investment, CreditCard, Debt, SavingsGoal, Bill, Account, Category, HouseholdMembership):
        await session.execute(delete(model).where(model.user_id == user.id))

    await session.execute(delete(Household).where(Household.created_by == user.id))


async def _seed_profile(session: AsyncSession, profile: dict[str, Any]) -> None:
    user = await _get_or_create_user(
        session,
        profile["email"],
        profile["password"],
        profile["full_name"],
    )
    await _reset_profile_data(session, user)
    await _get_or_create_household(session, user, profile["household_name"])

    accounts: dict[str, Account] = {}
    for name, type_, opening in profile["accounts"]:
        accounts[name] = await _get_or_create_account(session, user, name, type_, opening)

    categories: dict[str, Category] = {}
    for name, type_ in profile["categories"]:
        categories[name] = await _get_or_create_category(session, user, name, type_)

    monthly_income = sum(
        float(tx["amount"]) for tx in profile["monthly_transactions"] if float(tx["amount"]) > 0
    )

    for name, budget_value, category_name in profile["budgets"]:
        category = categories.get(category_name)
        amount = budget_value if abs(float(budget_value)) > 1 else monthly_income * float(budget_value)
        await _get_or_create_by_name(
            session,
            user,
            Budget,
            name,
            amount=amount,
            period="monthly",
            category_id=category.id if category else None,
        )

    for name, type_, symbol, cost_basis, current_value, account_name in profile.get("investments", []):
        await _get_or_create_by_name(
            session,
            user,
            Investment,
            name,
            type=type_,
            symbol=symbol,
            cost_basis=cost_basis,
            current_value=current_value,
            account_name=account_name,
        )

    for name, balance, credit_limit, apr, due_day in profile.get("credit_cards", []):
        await _get_or_create_by_name(
            session,
            user,
            CreditCard,
            name,
            balance=balance,
            credit_limit=credit_limit,
            apr=apr,
            payment_due_date=date(2026, TODAY.month if TODAY.month <= 12 else 12, min(due_day, 28)),
            min_payment=(balance * 0.05) + 25,
        )

    for name, type_, principal, interest_rate, min_payment, remaining_term_months in profile.get("debts", []):
        await _get_or_create_by_name(
            session,
            user,
            Debt,
            name,
            type=type_,
            principal=principal,
            interest_rate=interest_rate,
            min_payment=min_payment,
            payment_due_date=date(2026, TODAY.month if TODAY.month <= 12 else 12, 5),
            remaining_term_months=remaining_term_months,
        )

    for name, target_amount, current_amount, target_date in profile.get("savings_goals", []):
        await _get_or_create_by_name(
            session,
            user,
            SavingsGoal,
            name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
        )

    for name, amount, due_day, frequency, auto_pay in profile.get("bills", []):
        await _get_or_create_by_name(
            session,
            user,
            Bill,
            name,
            amount=amount,
            due_date=date(2026, TODAY.month if TODAY.month <= 12 else 12, min(due_day, 28)),
            frequency=frequency,
            auto_pay=auto_pay,
        )

    month_cursor = START_DATE.replace(day=1)
    month_index = 0
    while month_cursor <= date(TODAY.year, TODAY.month, 1):
        for tx in profile["monthly_transactions"]:
            tx_day = min(tx["day"], 28)
            tx_date = date(month_cursor.year, month_cursor.month, tx_day)
            if tx_date > TODAY:
                continue
            account = accounts.get(tx["account"])
            category = categories.get(tx["category"])
            if account is None:
                continue
            raw_amount = float(tx["amount"])
            if raw_amount >= 0:
                amount = raw_amount
            else:
                amount = _dynamic_amount(
                    raw_amount,
                    month_index,
                    profile.get("family_offset", 0),
                    float(profile.get("expense_variation", 0.12)),
                )
            signed_amount = amount if raw_amount >= 0 else -amount
            await _ensure_transaction(
                session,
                user,
                account,
                category,
                tx_date,
                signed_amount,
                tx["description"],
                tx["merchant"],
            )

        for item in profile.get("recurring_transactions", []):
            account = accounts.get(item["account"])
            category = categories.get(item["category"])
            if account is None:
                continue
            tx_date = date(month_cursor.year, month_cursor.month, min(int(item["day"]), 28))
            if tx_date > TODAY:
                continue
            raw_amount = float(item["amount"])
            if raw_amount >= 0:
                amount = raw_amount
            else:
                amount = _dynamic_amount(
                    raw_amount,
                    month_index,
                    profile.get("family_offset", 0) + 1,
                    float(profile.get("expense_variation", 0.12)) * 0.8,
                )
            signed_amount = amount if raw_amount >= 0 else -amount
            await _ensure_transaction(
                session,
                user,
                account,
                category,
                tx_date,
                signed_amount,
                item["name"],
                None,
            )

        month_cursor = date(month_cursor.year + (month_cursor.month // 12), ((month_cursor.month % 12) + 1), 1)
        month_index += 1

    for item in profile.get("recurring_transactions", []):
        account = accounts.get(item["account"])
        category = categories.get(item["category"])
        if account is None:
            continue
        await _ensure_recurring_transaction(session, user, account, category, item)

    await session.commit()
    print(f"Seeded user {user.email} (password: {profile['password']})")


async def main() -> None:
    await init_db()
    async with async_session() as session:
        for profile in SCENARIOS:
            await _seed_profile(session, profile)
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
