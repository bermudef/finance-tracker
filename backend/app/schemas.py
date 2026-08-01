from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class BudgetCreate(BaseModel):
    category_id: Optional[int] = None
    name: str
    amount: float
    period: str = "monthly"


class BudgetOut(BaseModel):
    id: int
    category_id: Optional[int]
    name: str
    amount: float
    period: str

    class Config:
        from_attributes = True
