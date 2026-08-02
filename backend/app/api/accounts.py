from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.database import get_db
from app.models.finance import Account, Transaction
from app.models.user import User
from app.schemas import AccountCreate, AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])

ACCOUNT_EXPORT_COLUMNS = ["name", "type", "currency", "opening_balance", "current_balance", "is_active"]


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Account)
        .where(Account.user_id == current_user.id)
        .order_by(Account.name)
    )
    return result.scalars().all()


@router.get("/export")
async def export_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the user's accounts as CSV, with current balances."""
    rows = (
        await db.execute(
            select(Account)
            .where(Account.user_id == current_user.id)
            .order_by(Account.name)
        )
    ).scalars().all()

    balances: dict[int, float] = {}
    if rows:
        sums = (
            await db.execute(
                select(Transaction.account_id, func.coalesce(func.sum(Transaction.amount), 0))
                .where(Transaction.user_id == current_user.id)
                .group_by(Transaction.account_id)
            )
        ).all()
        balances = {account_id: float(total) for account_id, total in sums}

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=ACCOUNT_EXPORT_COLUMNS)
    writer.writeheader()
    for a in rows:
        current = float(a.opening_balance or 0) + balances.get(a.id, 0.0)
        writer.writerow(
            {
                "name": a.name,
                "type": a.type,
                "currency": a.currency,
                "opening_balance": f"{float(a.opening_balance or 0):.2f}",
                "current_balance": f"{current:.2f}",
                "is_active": str(a.is_active),
            }
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=accounts.csv"},
    )


@router.post("", response_model=AccountOut)
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = Account(**data.model_dump(), user_id=current_user.id)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = await db.get(Account, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()
    return {"status": "deleted"}
