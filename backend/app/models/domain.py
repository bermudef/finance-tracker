from __future__ import annotations
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.models.database import Base


class CreditCard(Base):
    """Credit card account with billing details."""

    __tablename__ = "credit_cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False, default=0)
    credit_limit = Column(Numeric(12, 2), nullable=False, default=0)
    apr = Column(Numeric(5, 2), nullable=False, default=0)  # annual percentage rate
    payment_due_date = Column(Date, nullable=True)
    min_payment = Column(Numeric(12, 2), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Debt(Base):
    """Loans and obligations: mortgage, auto, student, personal, credit card."""

    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="other")  # mortgage, auto, student, personal, credit_card, other
    principal = Column(Numeric(12, 2), nullable=False, default=0)
    interest_rate = Column(Numeric(5, 2), nullable=False, default=0)  # annual %
    min_payment = Column(Numeric(12, 2), nullable=True)
    payment_due_date = Column(Date, nullable=True)
    remaining_term_months = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Investment(Base):
    """Holdings: stocks, ETFs, retirement accounts, crypto, etc."""

    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="other")  # stock, etf, retirement, crypto, cash, other
    symbol = Column(String(10), nullable=True)
    cost_basis = Column(Numeric(12, 2), nullable=False, default=0)  # total amount invested
    current_value = Column(Numeric(12, 2), nullable=False, default=0)  # current market value
    account_name = Column(String(100), nullable=True)  # e.g. "Fidelity 401k"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    target_amount = Column(Numeric(12, 2), nullable=False)
    current_amount = Column(Numeric(12, 2), nullable=False, default=0)
    target_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Bill(Base):
    """Recurring bills and subscriptions with due-date reminders."""

    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    frequency = Column(String(20), nullable=False, default="monthly")  # weekly, monthly, yearly
    auto_pay = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """User notifications: bill reminders, budget alerts, savings milestones."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(20), nullable=False)  # bill_reminder, budget_alert, savings_milestone, general
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
