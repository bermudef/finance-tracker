from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Accounts ----------


class AccountCreate(BaseModel):
    name: str
    type: str = "checking"
    currency: str = "USD"
    opening_balance: float = 0


class AccountOut(BaseModel):
    id: int
    name: str
    type: str
    currency: str
    opening_balance: float
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str
    type: str = "expense"
    color: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    type: str
    color: Optional[str]
    parent_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    account_id: int
    category_id: Optional[int] = None
    date: date
    amount: float
    description: Optional[str] = None
    merchant: Optional[str] = None
    status: str = "posted"


class TransactionOut(BaseModel):
    id: int
    account_id: int
    category_id: Optional[int]
    date: date
    amount: float
    description: Optional[str]
    merchant: Optional[str]
    status: str
    account_name: Optional[str] = None
    category_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BudgetCreate(BaseModel):
    category_id: Optional[int] = None
    name: str
    amount: float
    period: str = "monthly"
    rollover: bool = False


class BudgetUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    amount: Optional[float] = None
    period: Optional[str] = None
    rollover: Optional[bool] = None


class BudgetOut(BaseModel):
    id: int
    category_id: Optional[int]
    name: str
    amount: float
    period: str
    rollover: bool

    model_config = ConfigDict(from_attributes=True)


# ---------- Credit Cards ----------

class CreditCardCreate(BaseModel):
    name: str
    balance: float = 0
    credit_limit: float = 0
    apr: float = 0
    payment_due_date: Optional[date] = None
    min_payment: Optional[float] = None


class CreditCardOut(BaseModel):
    id: int
    name: str
    balance: float
    credit_limit: float
    apr: float
    payment_due_date: Optional[date] = None
    min_payment: Optional[float] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CreditCardUpdate(BaseModel):
    name: Optional[str] = None
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    apr: Optional[float] = None
    payment_due_date: Optional[date] = None
    min_payment: Optional[float] = None
    is_active: Optional[bool] = None


# ---------- Debts ----------

class DebtCreate(BaseModel):
    name: str
    type: str = "other"
    principal: float = 0
    interest_rate: float = 0
    min_payment: Optional[float] = None
    payment_due_date: Optional[date] = None
    remaining_term_months: Optional[int] = None


class DebtOut(BaseModel):
    id: int
    name: str
    type: str
    principal: float
    interest_rate: float
    min_payment: Optional[float] = None
    payment_due_date: Optional[date] = None
    remaining_term_months: Optional[int] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class DebtUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    principal: Optional[float] = None
    interest_rate: Optional[float] = None
    min_payment: Optional[float] = None
    payment_due_date: Optional[date] = None
    remaining_term_months: Optional[int] = None
    is_active: Optional[bool] = None


# ---------- Investments ----------

class InvestmentCreate(BaseModel):
    name: str
    type: str = "other"
    symbol: Optional[str] = None
    cost_basis: float = 0
    current_value: float = 0
    account_name: Optional[str] = None
    notes: Optional[str] = None


class InvestmentOut(BaseModel):
    id: int
    name: str
    type: str
    symbol: Optional[str] = None
    cost_basis: float
    current_value: float
    account_name: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InvestmentUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    symbol: Optional[str] = None
    cost_basis: Optional[float] = None
    current_value: Optional[float] = None
    account_name: Optional[str] = None
    notes: Optional[str] = None


# ---------- Savings Goals ----------

class SavingsGoalCreate(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0
    target_date: Optional[date] = None
    notes: Optional[str] = None


class SavingsGoalOut(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    target_date: Optional[date] = None
    is_active: bool
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    target_date: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


# ---------- Bills ----------

class BillCreate(BaseModel):
    name: str
    amount: float
    due_date: date
    frequency: str = "monthly"
    auto_pay: bool = False
    notes: Optional[str] = None


class BillOut(BaseModel):
    id: int
    name: str
    amount: float
    due_date: date
    frequency: str
    auto_pay: bool
    is_active: bool
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BillUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[date] = None
    frequency: Optional[str] = None
    auto_pay: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
