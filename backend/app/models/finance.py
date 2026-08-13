from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, Date, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.models.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="checking")  # checking, savings, credit, cash
    currency = Column(String(3), nullable=False, default="USD")
    opening_balance = Column(Numeric(12, 2), nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="expense")  # income, expense
    color = Column(String(20), nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    recurring_id = Column(Integer, ForeignKey("recurring_transactions.id"), nullable=True, index=True)
    date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)  # positive=income, negative=expense
    description = Column(String(255), nullable=True)
    merchant = Column(String(100), nullable=True)
    status = Column(String(20), default="posted")  # posted, pending, cleared
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    period = Column(String(20), default="monthly")  # weekly, monthly, yearly
    rollover = Column(Boolean, default=False)  # carry unused budget into next month
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="budgets")
    category = relationship("Category")


class RecurringTransaction(Base):
    """Transactions that repeat on a schedule (rent, gym, subscriptions).

    Due items are materialized into the transactions table by
    ``app.services.recurring.process_due_recurring`` — the same helper that
    schedules bill reminders, so day-of-month overflow clamps the same way.
    """

    __tablename__ = "recurring_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)  # positive=income, negative=expense
    frequency = Column(String(20), nullable=False, default="monthly")  # weekly, monthly, yearly
    next_date = Column(Date, nullable=False, index=True)  # next occurrence to post
    auto_pay = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    account = relationship("Account")
    category = relationship("Category")
