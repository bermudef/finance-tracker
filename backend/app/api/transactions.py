from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Account, Category, Transaction
from app.models.user import User
from app.schemas import TransactionCreate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _owns_account(db: AsyncSession, user: User, account_id: int) -> Account | None:
    account = await db.get(Account, account_id)
    if account and account.user_id == user.id:
        return account
    return None


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if category_id:
        query = query.where(Transaction.category_id == category_id)
    if start:
        query = query.where(Transaction.date >= start)
    if end:
        query = query.where(Transaction.date <= end)
    query = query.limit(limit)

    result = await db.execute(query)
    txs = result.scalars().all()

    account_names = {}
    category_names = {}
    if txs:
        account_ids = {t.account_id for t in txs}
        category_ids = {t.category_id for t in txs if t.category_id}
        if account_ids:
            acc_result = await db.execute(select(Account).where(Account.id.in_(account_ids)))
            account_names = {a.id: a.name for a in acc_result.scalars()}
        if category_ids:
            cat_result = await db.execute(select(Category).where(Category.id.in_(category_ids)))
            category_names = {c.id: c.name for c in cat_result.scalars()}

    out = []
    for t in txs:
        item = TransactionOut.model_validate(t)
        item.account_name = account_names.get(t.account_id)
        item.category_name = category_names.get(t.category_id)
        out.append(item)
    return out


@router.post("", response_model=TransactionOut)
async def create_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = await _owns_account(db, current_user, data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if data.category_id:
        category = await db.get(Category, data.category_id)
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Category not found")
    tx = Transaction(**data.model_dump(), user_id=current_user.id)
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    item = TransactionOut.model_validate(tx)
    item.account_name = account.name
    if tx.category_id:
        category = await db.get(Category, tx.category_id)
        item.category_name = category.name if category else None
    return item


@router.put("/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: int,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tx = await db.get(Transaction, transaction_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    account = await _owns_account(db, current_user, data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if data.category_id:
        category = await db.get(Category, data.category_id)
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Category not found")
    for key, val in data.model_dump().items():
        setattr(tx, key, val)
    await db.commit()
    await db.refresh(tx)
    item = TransactionOut.model_validate(tx)
    item.account_name = account.name
    if tx.category_id:
        category = await db.get(Category, tx.category_id)
        item.category_name = category.name if category else None
    return item


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tx = await db.get(Transaction, transaction_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(tx)
    await db.commit()
    return {"status": "deleted"}
