"""Recurring transactions — schedules that auto-post into the transactions table."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Account, Category, RecurringTransaction, Transaction
from app.models.user import User
from app.services.recurring import list_recurring, process_due_recurring

router = APIRouter(prefix="/recurring-transactions", tags=["recurring-transactions"])

VALID_FREQUENCIES = ("weekly", "monthly", "yearly")


class RecurringTransactionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    account_id: int
    category_id: Optional[int] = None
    amount: float = Field(description="Positive = income, negative = expense")
    frequency: str = Field(default="monthly")
    next_date: date
    notes: Optional[str] = Field(default=None, max_length=500)


class RecurringTransactionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    amount: Optional[float] = None
    frequency: Optional[str] = None
    next_date: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class RecurringTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    account_id: int
    category_id: Optional[int] = None
    name: str
    amount: float
    frequency: str
    next_date: date
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime


class ProcessResult(BaseModel):
    posted: int
    message: str


async def _validate_account_category(db: AsyncSession, user_id: int, account_id: int, category_id: Optional[int]):
    """Ownership checks for account/category references; 404 if not the user's."""
    account = await db.get(Account, account_id)
    if not account or account.user_id != user_id:
        raise HTTPException(status_code=404, detail="Account not found")
    if category_id is not None:
        category = await db.get(Category, category_id)
        if not category or category.user_id != user_id:
            raise HTTPException(status_code=404, detail="Category not found")


@router.get("", response_model=list[RecurringTransactionOut])
async def get_recurring(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_recurring(db, current_user.id)


@router.post("", response_model=RecurringTransactionOut, status_code=201)
async def create_recurring(
    data: RecurringTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.frequency not in VALID_FREQUENCIES:
        raise HTTPException(status_code=422, detail=f"frequency must be one of {VALID_FREQUENCIES}")
    if data.amount == 0:
        raise HTTPException(status_code=422, detail="amount must be non-zero")
    await _validate_account_category(db, current_user.id, data.account_id, data.category_id)

    item = RecurringTransaction(
        user_id=current_user.id,
        name=data.name,
        account_id=data.account_id,
        category_id=data.category_id,
        amount=data.amount,
        frequency=data.frequency,
        next_date=data.next_date,
        notes=data.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/{item_id}", response_model=RecurringTransactionOut)
async def update_recurring(
    item_id: int,
    data: RecurringTransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await db.get(RecurringTransaction, item_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")

    updates = data.model_dump(exclude_unset=True)
    if "frequency" in updates and updates["frequency"] not in VALID_FREQUENCIES:
        raise HTTPException(status_code=422, detail=f"frequency must be one of {VALID_FREQUENCIES}")
    if "account_id" in updates or "category_id" in updates:
        await _validate_account_category(
            db, current_user.id,
            updates.get("account_id", item.account_id),
            updates.get("category_id", item.category_id),
        )
    if "amount" in updates and updates["amount"] == 0:
        raise HTTPException(status_code=422, detail="amount must be non-zero")

    for key, value in updates.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}")
async def delete_recurring(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await db.get(RecurringTransaction, item_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    await db.delete(item)
    await db.commit()
    return {"status": "deleted"}


@router.post("/process", response_model=ProcessResult)
async def process_due(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Post all due recurring transactions now and roll their schedules forward."""
    created = await process_due_recurring(db, current_user.id)
    return {
        "posted": len(created),
        "message": f"Posted {len(created)} recurring transaction(s)."
        if created
        else "Nothing due right now.",
    }
